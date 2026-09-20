from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import AuditLog, User, UserRole
from backend.security import require_roles

router = APIRouter(prefix="/audit", tags=["Audit Logging"])

@router.get("/logs")
async def get_audit_logs(
    resource: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([
        UserRole.SYSTEM_ADMIN.value,
        UserRole.STATE_OFFICER.value,
        UserRole.DISTRICT_OFFICER.value
    ]))
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if resource:
        stmt = stmt.where(AuditLog.resource == resource)
        
    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": l.id,
            "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user": l.user_name or "System",
            "role": l.role or "SYSTEM",
            "action": l.action,
            "module": l.resource,
            "description": f"{l.action} on {l.resource} #{l.resource_id or ''}",
            "ip": l.ip_address or "127.0.0.1",
            "result": "Success" if l.success else "Failed"
        }
        for l in logs
    ]
