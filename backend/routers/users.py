from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.database import get_db
from backend.models import User, UserRole
from backend.schemas import UserProfile
from backend.security import get_current_user, require_roles
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/users", tags=["Users & RBAC"])

@router.get("", response_model=List[UserProfile])
async def list_users(
    role: Optional[str] = None,
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([
        UserRole.DISTRICT_OFFICER.value,
        UserRole.STATE_OFFICER.value,
        UserRole.SYSTEM_ADMIN.value
    ]))
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if district:
        stmt = stmt.where(User.district == district)
        
    result = await db.execute(stmt)
    return result.scalars().all()

@router.patch("/{user_id}/status")
async def toggle_user_status(
    user_id: str,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.SYSTEM_ADMIN.value, UserRole.STATE_OFFICER.value]))
):
    stmt = select(User).where(User.id == user_id)
    target_user = (await db.execute(stmt)).scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_status = target_user.is_active
    target_user.is_active = is_active
    await db.commit()
    
    await AuditService.log(
        db, action="USER_STATUS_UPDATE", resource="USER", resource_id=user_id,
        user_id=current_user.id, user_name=current_user.full_name, role=current_user.role,
        old_value={"is_active": old_status}, new_value={"is_active": is_active}
    )
    return {"message": "Status updated successfully", "user_id": user_id, "is_active": is_active}
