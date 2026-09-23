from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import AuditLog, User
from backend.security import Permission, jurisdiction_scope, require_permission

router = APIRouter(prefix="/audit", tags=["Audit Logging"])


@router.get("/logs")
async def get_audit_logs(resource: Optional[str] = None, action: Optional[str] = None, user_id: Optional[str] = None,
                         limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                         db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.AUDIT_READ))):
    stmt = select(AuditLog)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if jurisdiction_scope(current_user)["district"]:
        # district/block officers see actions performed by users in their district
        stmt = stmt.where(AuditLog.user_id.in_(select(User.id).where(User.district == current_user.district)))
    logs = (await db.execute(stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return [{"id": entry.id, "timestamp": entry.created_at.strftime("%Y-%m-%d %H:%M:%S"), "user": entry.user_name or "System", "role": entry.role or "SYSTEM",
             "action": entry.action, "module": entry.resource, "description": f"{entry.action} on {entry.resource} #{entry.resource_id or ''}",
             "ip": entry.ip_address, "requestId": entry.request_id, "result": "Success" if entry.success else "Failed"} for entry in logs]
