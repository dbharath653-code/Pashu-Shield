"""Publish call.* realtime events over the EXISTING WebSocket infrastructure
(services/events.py + services/websocket_manager.py — no second channel is created).

Delivery is filtered per connection by role/jurisdiction: events carry the report's
district when known so only vets/officers of that district (plus the farmer owner)
receive them — see websocket_manager._can_receive.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.events import Event


async def publish_call_event(name: str, session, data: Optional[Dict[str, Any]] = None) -> None:
    """`name` must be registered in events.EVENT_NAMES (e.g. 'call.started').
    District comes from the session column (farmer profile / report) so the existing
    WebSocket manager delivers only within jurisdiction."""
    payload = {
        "callSessionId": session.id,
        "status": session.status,
        "language": session.language,
        "provider": session.provider,
        "isSimulated": bool(session.is_simulated),
        "callerMasked": _mask(session.caller_phone),
        "reportId": session.disease_report_id,
        "district": getattr(session, "district", None),
        **(data or {}),
    }
    await Event(
        name,
        payload,
        district=getattr(session, "district", None),
        owner_id=session.farmer_id,
        user_ids=[session.veterinarian_id] if session.veterinarian_id else [],
        roles=None,
    ).publish()


def _mask(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone
    digits = str(phone)
    return ("*" * max(0, len(digits) - 4)) + digits[-4:]
