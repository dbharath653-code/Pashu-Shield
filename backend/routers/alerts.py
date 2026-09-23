from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import Alert, Notification, User, UserRole
from backend.security import Permission, jurisdiction_scope, require_permission

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])


def _serialize(a: Alert, user: User) -> dict:
    return {"id": a.id, "time": a.created_at.strftime("%d %b %Y - %I:%M %p"), "createdAt": a.created_at.isoformat(), "title": a.title,
            "type": a.type, "alertType": a.alert_type, "severity": a.severity, "message": a.message, "district": a.district, "disease": a.disease,
            "evidenceLevel": a.evidence_level, "occurrences": a.occurrences, "lastOccurredAt": a.last_occurred_at.isoformat() if a.last_occurred_at else None,
            "relatedEntity": {"type": a.related_entity_type, "id": a.related_entity_id} if a.related_entity_id else None,
            "read": user.id in (a.read_by or []), "isDemo": a.is_demo}


@router.get("")
async def get_alerts(district: Optional[str] = None, limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_permission(Permission.ALERT_READ))):
    stmt = select(Alert).order_by(Alert.last_occurred_at.desc())
    scope = jurisdiction_scope(current_user)
    if scope["district"]:
        # users see alerts for their district plus state-wide broadcasts
        stmt = stmt.where(or_(Alert.district == scope["district"], Alert.district.is_(None), Alert.is_broadcast.is_(True)))
    elif district:
        stmt = stmt.where(Alert.district == district)
    if settings.DATA_MODE == "live":
        stmt = stmt.where(Alert.is_demo.is_(False))
    rows = (await db.execute(stmt.limit(limit * 2))).scalars().all()
    visible = [a for a in rows if not a.target_roles or current_user.role in a.target_roles or current_user.role == UserRole.SYSTEM_ADMIN.value
               or current_user.role == UserRole.FARMER.value and a.is_broadcast]
    return [_serialize(a, current_user) for a in visible[:limit]]


@router.post("/{alert_id}/read")
async def mark_read(alert_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.ALERT_READ))):
    a = await db.get(Alert, alert_id)
    if not a:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "Alert not found"})
    if current_user.id not in (a.read_by or []):
        a.read_by = [*(a.read_by or []), current_user.id]
        await db.commit()
    return {"success": True}


@router.get("/notifications/mine")
async def my_notifications(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_permission(Permission.ALERT_READ))):
    rows = (await db.execute(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(limit))).scalars().all()
    return [{"id": n.id, "channel": n.channel, "template": n.template, "content": n.content, "status": n.status, "provider": n.provider,
             "failureReason": n.failure_reason, "createdAt": n.created_at.isoformat(), "deliveredAt": n.delivered_at.isoformat() if n.delivered_at else None} for n in rows]
