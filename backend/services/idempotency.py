"""HTTP Idempotency-Key support for offline-created mutations.

Same key + same user + same body  -> stored response replayed (no duplicate record).
Same key + different body         -> 422 IDEMPOTENCY_KEY_REUSED.
Concurrent duplicate in flight    -> 409 IDEMPOTENCY_IN_PROGRESS (client retries later).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.database import AsyncSessionLocal
from backend.models import IdempotencyRecord


def body_hash(body: Any) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


async def begin(scope: str, key: Optional[str], method: str, path: str, body: Any) -> Optional[dict]:
    """Returns a replay dict {'status_code', 'body'} if already completed; otherwise reserves the key."""
    if not key:
        return None
    if len(key) > 128:
        raise HTTPException(status_code=422, detail={"code": "INVALID_IDEMPOTENCY_KEY", "message": "Idempotency-Key too long"})
    h = body_hash(body)
    async with AsyncSessionLocal() as db:
        rec = (await db.execute(select(IdempotencyRecord).where(IdempotencyRecord.user_scope == scope, IdempotencyRecord.key == key))).scalars().first()
        if rec:
            if rec.request_hash != h or rec.path != path:
                raise HTTPException(status_code=422, detail={"code": "IDEMPOTENCY_KEY_REUSED", "message": "Idempotency-Key was already used with a different request"})
            if rec.state == "COMPLETED":
                return {"status_code": rec.status_code, "body": rec.response_body}
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_IN_PROGRESS", "message": "An identical request is still being processed"})
        db.add(IdempotencyRecord(id=uuid.uuid4().hex, user_scope=scope, key=key, method=method, path=path, request_hash=h, state="IN_PROGRESS"))
        try:
            await db.commit()
        except IntegrityError:
            raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_IN_PROGRESS", "message": "An identical request is still being processed"})
    return None


async def complete(scope: str, key: Optional[str], status_code: int, body: Any) -> None:
    if not key:
        return
    async with AsyncSessionLocal() as db:
        rec = (await db.execute(select(IdempotencyRecord).where(IdempotencyRecord.user_scope == scope, IdempotencyRecord.key == key))).scalars().first()
        if rec:
            rec.state, rec.status_code, rec.response_body = "COMPLETED", status_code, json.loads(json.dumps(body, default=str))
            await db.commit()


async def abandon(scope: str, key: Optional[str]) -> None:
    """Release the key after a failure so the client can retry."""
    if not key:
        return
    async with AsyncSessionLocal() as db:
        rec = (await db.execute(select(IdempotencyRecord).where(IdempotencyRecord.user_scope == scope, IdempotencyRecord.key == key, IdempotencyRecord.state == "IN_PROGRESS"))).scalars().first()
        if rec:
            await db.delete(rec)
            await db.commit()
