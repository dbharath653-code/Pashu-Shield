import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import AuditLog

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
        success: bool = True
    ):
        try:
            entry = AuditLog(
                id=str(uuid.uuid4()),
                action=action,
                resource=resource,
                resource_id=resource_id,
                user_id=user_id,
                user_name=user_name,
                role=role,
                old_value=old_value,
                new_value=new_value,
                ip_address=ip_address,
                success=success,
                created_at=datetime.utcnow()
            )
            db.add(entry)
            await db.commit()
        except Exception as e:
            print(f"Warning: Failed to write audit log: {e}")
