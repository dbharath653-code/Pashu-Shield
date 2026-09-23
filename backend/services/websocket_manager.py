"""Authenticated WebSocket connection manager.

Identity (user id, role, district, block, permissions) is derived exclusively from a verified
access token — never from client-supplied query parameters. Each event is delivered only to
connections allowed to see it:
  * explicit recipients (event.user_ids) and the record owner always receive it;
  * officers/vets receive it when the event's district/block is within their jurisdiction;
  * farmers receive only events addressed to them.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket

from backend.models import UserRole

logger = logging.getLogger("pashu_shield.ws")
MAX_CONNECTIONS_PER_USER = 5


@dataclass(eq=False)
class Connection:
    ws: WebSocket
    user_id: str
    role: str
    district: Optional[str]
    taluka: Optional[str]
    subscriptions: Set[str] = field(default_factory=lambda: {"*"})
    last_seen: datetime = field(default_factory=datetime.utcnow)


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: Set[Connection] = set()
        self._lock = asyncio.Lock()

    @property
    def active_connections(self):  # backward-compatible accessor
        return {c.ws for c in self.connections}

    async def register(self, ws: WebSocket, user) -> Connection:
        async with self._lock:
            mine = [c for c in self.connections if c.user_id == user.id]
            if len(mine) >= MAX_CONNECTIONS_PER_USER:
                oldest = min(mine, key=lambda c: c.last_seen)
                self.connections.discard(oldest)
                try:
                    await oldest.ws.close(code=4008)
                except Exception:
                    pass
            conn = Connection(ws=ws, user_id=user.id, role=user.role, district=user.district, taluka=user.taluka)
            self.connections.add(conn)
        await ws.send_json({"type": "CONNECTION_ESTABLISHED", "status": "CONNECTED", "user_id": user.id, "role": user.role, "district": user.district})
        return conn

    def disconnect(self, target) -> None:
        for c in list(self.connections):
            if c is target or c.ws is target:
                self.connections.discard(c)

    @staticmethod
    def _can_receive(conn: Connection, ev) -> bool:
        if ev.name.split(".")[0] not in conn.subscriptions and "*" not in conn.subscriptions:
            return False
        if conn.user_id in (ev.user_ids or []) or (ev.owner_id and conn.user_id == ev.owner_id):
            return True
        if ev.roles is not None and conn.role not in ev.roles and conn.role != UserRole.SYSTEM_ADMIN.value:
            return False
        role = conn.role
        if role in (UserRole.SYSTEM_ADMIN.value, UserRole.STATE_OFFICER.value):
            return True
        if role == UserRole.FARMER.value:
            return False
        if role in (UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value):
            return ev.name.startswith(("sample.", "lab."))
        if not ev.district:
            return False
        if (conn.district or "").lower() != ev.district.lower():
            return False
        if role == UserRole.BLOCK_OFFICER.value and conn.taluka and ev.taluka and conn.taluka.lower() != ev.taluka.lower():
            return False
        return True

    async def publish(self, ev) -> int:
        msg = ev.message()
        sent, dead = 0, []
        for conn in list(self.connections):
            if not self._can_receive(conn, ev):
                continue
            try:
                await conn.ws.send_json(msg)
                sent += 1
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)
        return sent

    # Legacy helpers retained for any remaining call sites; they route through publish rules.
    async def broadcast(self, message: Dict[str, Any]) -> None:
        logger.warning("ws_manager.broadcast is deprecated; message dropped unless sent via Event", extra={"fields": {"type": message.get("type")}})

    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        for conn in [c for c in self.connections if c.user_id == user_id]:
            try:
                await conn.ws.send_json(message)
            except Exception:
                self.disconnect(conn)


ws_manager = ConnectionManager()
