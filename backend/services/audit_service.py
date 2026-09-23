"""Append-only audit logging. Application code only INSERTs audit rows; no update/delete path
exists. Secrets are stripped from before/after snapshots."""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditLog

logger = logging.getLogger("pashu_shield.audit")
_SENSITIVE = {"password", "hashed_password", "token", "access_token", "refresh_token", "api_key", "secret", "otp"}


def _scrub(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return value
    return {k: ("[REDACTED]" if k.lower() in _SENSITIVE else _scrub(v) if isinstance(v, dict) else v) for k, v in value.items()}


class AuditService:
    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        role: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        commit: bool = True,
    ) -> Optional[AuditLog]:
        try:
            entry = AuditLog(
                id=f"AUD-{uuid.uuid4().hex[:12].upper()}",
                user_id=user_id, user_name=user_name, role=role,
                action=action, resource=resource, resource_id=resource_id,
                old_value=_scrub(old_value), new_value=_scrub(new_value),
                ip_address=ip_address, request_id=request_id, session_id=session_id,
                success=success, created_at=datetime.utcnow(),
            )
            db.add(entry)
            if commit:
                await db.commit()
            return entry
        except Exception:  # auditing must never take down the primary workflow, but must be visible
            logger.exception("Failed to write audit log", extra={"fields": {"action": action, "resource": resource}})
            return None

    @staticmethod
    async def for_user(db: AsyncSession, user, action: str, resource: str, resource_id: Optional[str] = None, request=None, commit: bool = True, **kw):
        return await AuditService.log(
            db, action=action, resource=resource, resource_id=resource_id,
            user_id=getattr(user, "id", None), user_name=getattr(user, "full_name", None), role=getattr(user, "role", None),
            ip_address=(request.client.host if request is not None and request.client else None),
            request_id=(getattr(request.state, "request_id", None) if request is not None else None),
            commit=commit, **kw,
        )
