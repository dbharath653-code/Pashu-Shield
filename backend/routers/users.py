from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import User, UserRole
from backend.schemas import UserProfile
from backend.security import Permission, forbidden, in_jurisdiction, require_permission, resolve_district_filter, revoke_all_user_sessions
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["Users & RBAC"])

# Who may assign which role. SYSTEM_ADMIN is only assignable by SYSTEM_ADMIN.
_ASSIGNABLE = {
    UserRole.SYSTEM_ADMIN.value: {r.value for r in UserRole},
    UserRole.STATE_OFFICER.value: {r.value for r in UserRole} - {UserRole.SYSTEM_ADMIN.value},
}


@router.get("", response_model=List[UserProfile])
async def list_users(role: Optional[str] = None, district: Optional[str] = None, pending: Optional[bool] = None, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_permission(Permission.REPORT_ASSIGN))):
    stmt = select(User)
    d = resolve_district_filter(current_user, district)
    if d:
        stmt = stmt.where(User.district == d)
    if role:
        stmt = stmt.where(User.role == role)
    if pending is not None:
        stmt = stmt.where(User.is_verified.is_(not pending))
    return (await db.execute(stmt.limit(500))).scalars().all()


class VerifyUser(BaseModel):
    approve: bool = True
    role: Optional[str] = Field(default=None, max_length=32)


@router.post("/{user_id}/verify")
async def verify_user(user_id: str, req: VerifyUser, request: Request, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_permission(Permission.USER_MANAGE))):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    if target.id == current_user.id:
        raise forbidden("You cannot verify your own account")
    allowed = _ASSIGNABLE.get(current_user.role, set())
    if req.role and req.role not in allowed:
        raise forbidden("You cannot assign this role", code="ROLE_NOT_ASSIGNABLE")
    old = {"role": target.role, "is_verified": target.is_verified}
    target.is_verified = req.approve
    if req.role:
        target.role = req.role
    await AuditService.for_user(db, current_user, "USER_VERIFIED" if req.approve else "USER_VERIFICATION_REVOKED", "USER", user_id, request=request, commit=False,
                                old_value=old, new_value={"role": target.role, "is_verified": target.is_verified})
    if not req.approve or req.role:
        await revoke_all_user_sessions(db, user_id, "ROLE_CHANGED")
    await db.commit()
    return {"user_id": user_id, "role": target.role, "is_verified": target.is_verified}


@router.patch("/{user_id}/status")
async def toggle_user_status(user_id: str, is_active: bool, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(require_permission(Permission.USER_MANAGE))):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail={"code": "USER_NOT_FOUND", "message": "User not found"})
    if target.role == UserRole.SYSTEM_ADMIN.value and current_user.role != UserRole.SYSTEM_ADMIN.value:
        raise forbidden()
    if not in_jurisdiction(current_user, target.district):
        raise forbidden("User outside your jurisdiction", code="OUT_OF_JURISDICTION")
    old = target.is_active
    target.is_active = is_active
    if not is_active:
        await revoke_all_user_sessions(db, user_id, "DEACTIVATED")
    await AuditService.for_user(db, current_user, "USER_STATUS_UPDATE", "USER", user_id, request=request, commit=False, old_value={"is_active": old}, new_value={"is_active": is_active})
    await db.commit()
    return {"message": "Status updated successfully", "user_id": user_id, "is_active": is_active}
