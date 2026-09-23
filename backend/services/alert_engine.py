"""Centralised alert generation with deduplication and evidence labelling."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Alert

ALERT_TYPES = {"HIGH_RISK_REPORT", "CRITICAL_REPORT", "LAB_RESULT", "OUTBREAK", "VACCINATION_DUE", "VACCINATION_CAMPAIGN", "WEATHER_RISK", "SYSTEM_FAILURE", "DATA_SOURCE_FAILURE"}
SEVERITIES = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
EVIDENCE_LABELS = {"REPORTED", "UNDER_VERIFICATION", "VETERINARIAN_VERIFIED", "LAB_CONFIRMED", "PREDICTED_RISK", "FORECAST"}
_UI_TYPE = {"CRITICAL": "high", "HIGH": "warning", "MEDIUM": "warning", "LOW": "info", "INFO": "info"}


async def raise_alert(
    db: AsyncSession,
    *,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    dedup_key: str,
    district: Optional[str] = None,
    taluka: Optional[str] = None,
    disease: Optional[str] = None,
    target_roles: Optional[List[str]] = None,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[str] = None,
    evidence_level: str = "REPORTED",
    is_demo: bool = False,
) -> tuple[Alert, bool]:
    """Create or bump an alert. Returns (alert, created). Caller commits."""
    assert alert_type in ALERT_TYPES, alert_type
    assert severity in SEVERITIES, severity
    assert evidence_level in EVIDENCE_LABELS, evidence_level
    existing = (await db.execute(select(Alert).where(Alert.dedup_key == dedup_key))).scalars().first()
    if existing:
        existing.occurrences = (existing.occurrences or 1) + 1
        existing.last_occurred_at = datetime.utcnow()
        order = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if order.index(severity) > order.index(existing.severity if existing.severity in order else "INFO"):
            existing.severity, existing.type = severity, _UI_TYPE[severity]
        return existing, False
    alert = Alert(
        id=f"ALT-{uuid.uuid4().hex[:10].upper()}",
        alert_code=f"ALR-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        alert_type=alert_type, type=_UI_TYPE[severity], severity=severity,
        title=f"[{evidence_level.replace('_', ' ')}] {title}"[:255], message=message,
        district=district, taluka=taluka, disease=disease,
        is_broadcast=not target_roles, target_roles=target_roles or [],
        dedup_key=dedup_key[:191], related_entity_type=related_entity_type, related_entity_id=related_entity_id,
        evidence_level=evidence_level, is_demo=is_demo,
    )
    db.add(alert)
    return alert, True
