from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import Alert, User
from backend.security import get_current_user_optional

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])

@router.get("")
async def get_alerts(district: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(50)
    alerts = (await db.execute(stmt)).scalars().all()
    
    return [
        {
            "id": a.id,
            "time": a.created_at.strftime("%d %b %Y - %I:%M %p"),
            "title": a.title,
            "type": a.type,
            "severity": a.severity,
            "message": a.message,
            "district": a.district,
            "disease": a.disease
        }
        for a in alerts
    ]
