from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import DiseaseReport, User, UserRole, WorkflowEvent
from backend.schemas import DiseaseReportCreate, ReportVerifyRequest
from backend.security import (Permission, ensure_can_access_record, forbidden, jurisdiction_scope, require_permission,
                              resolve_district_filter)
from backend.services import idempotency
from backend.services.alert_engine import raise_alert
from backend.services.audit_service import AuditService
from backend.services.events import Event
from backend.services.rate_limit import enforce
from backend.services.report_service import serialize_report, submit_report
from backend.services.workflow import normalize_status, transition

router = APIRouter(prefix="/reports", tags=["Disease Reports & Triage"])


def scoped_reports_query(user: User, district: Optional[str]):
    stmt = select(DiseaseReport).where(DiseaseReport.deleted_at.is_(None))
    if user.role == UserRole.FARMER.value:
        return stmt.where(DiseaseReport.user_id == user.id)
    if user.role in (UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value):
        raise forbidden()
    d = resolve_district_filter(user, district)
    if d:
        stmt = stmt.where(DiseaseReport.district == d)
    scope = jurisdiction_scope(user)
    if scope["taluka"]:
        stmt = stmt.where(DiseaseReport.taluka == scope["taluka"])
    return stmt


@router.get("")
async def get_reports(
    district: Optional[str] = None,
    species: Optional[str] = None,
    status: Optional[str] = None,
    verification_status: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_READ)),
):
    """Paginated, jurisdiction-scoped list. Returns a JSON array (legacy contract) with
    pagination metadata in X-Total-Count / X-Next-Offset headers."""
    from fastapi.responses import JSONResponse
    stmt = scoped_reports_query(current_user, district)
    if species:
        stmt = stmt.where(DiseaseReport.species == species)
    if status:
        stmt = stmt.where(DiseaseReport.status == normalize_status(status))
    if verification_status:
        stmt = stmt.where(DiseaseReport.verification_status == verification_status)
    if since:
        stmt = stmt.where(DiseaseReport.created_at >= since.replace(tzinfo=None))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    rows = (await db.execute(stmt.order_by(DiseaseReport.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    headers = {"X-Total-Count": str(total)}
    if offset + len(rows) < total:
        headers["X-Next-Offset"] = str(offset + len(rows))
    return JSONResponse([serialize_report(r) for r in rows], headers=headers)


@router.post("")
async def submit_disease_report(
    req: DiseaseReportCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_CREATE)),
):
    await enforce("report", current_user.id)
    key = idempotency_key or req.idempotency_key
    replay = await idempotency.begin(current_user.id, key, "POST", "/reports", req.model_dump(mode="json", exclude={"idempotency_key"}))
    if replay:
        return {**replay["body"], "idempotent_replay": True}
    try:
        result = await submit_report(db, req, current_user, source="VOICE" if req.channel == "VOICE" else "LIVE", request=request)
    except Exception:
        await idempotency.abandon(current_user.id, key)
        raise
    await idempotency.complete(current_user.id, key, 200, result)
    return result


@router.get("/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.REPORT_READ))):
    r = await db.get(DiseaseReport, report_id)
    if r is None or r.deleted_at is not None:
        # tracking ID lookup
        r = (await db.execute(select(DiseaseReport).where(DiseaseReport.report_number == report_id))).scalars().first()
    if r is None:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "Disease report was not found."})
    ensure_can_access_record(current_user, owner_ids=[r.user_id], district=r.district, taluka=r.taluka)
    history = (await db.execute(select(WorkflowEvent).where(WorkflowEvent.entity_type == "REPORT", WorkflowEvent.entity_id == r.id).order_by(WorkflowEvent.created_at))).scalars().all()
    return {**serialize_report(r), "history": [{"from": h.from_status, "to": h.to_status, "at": h.created_at.isoformat(), "note": h.note} for h in history]}


@router.post("/{report_id}/verify")
async def verify_report(report_id: str, req: ReportVerifyRequest, request: Request, db: AsyncSession = Depends(get_db),
                        current_user: User = Depends(require_permission(Permission.REPORT_VERIFY))):
    """Veterinary confirmation (human-in-the-loop). Only vets/officers in jurisdiction."""
    r = await db.get(DiseaseReport, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "Disease report was not found."})
    ensure_can_access_record(current_user, district=r.district, taluka=r.taluka)
    before = {"verification_status": r.verification_status, "disease": r.suspected_disease, "status": r.status}
    r.verification_status = req.verification_status
    r.verified_by_id, r.verified_at = current_user.id, datetime.utcnow()
    if req.confirmed_disease:
        r.suspected_disease = req.confirmed_disease
    if req.verification_status == "VERIFIED":
        if normalize_status(r.status) in ("VISITED", "RESULT_AVAILABLE"):
            transition(db, "REPORT", r, "VERIFIED", current_user, note=req.notes)
        await raise_alert(db, alert_type="HIGH_RISK_REPORT", severity="HIGH" if r.triage_risk_level != "CRITICAL" else "CRITICAL",
                          title=f"Veterinarian-verified {r.suspected_disease} – {r.district}", message=f"Report {r.report_number} verified by a veterinarian.",
                          dedup_key=f"verified:{r.id}", district=r.district, taluka=r.taluka, disease=r.suspected_disease,
                          related_entity_type="REPORT", related_entity_id=r.id, evidence_level="VETERINARIAN_VERIFIED", is_demo=r.is_demo)
    r.version += 1
    await AuditService.for_user(db, current_user, "REPORT_VERIFIED", "REPORT", r.id, request=request, commit=False, old_value=before, new_value={"verification_status": r.verification_status, "disease": r.suspected_disease})
    await db.commit()
    await Event("report.verified", {"id": r.id, "verificationStatus": r.verification_status, "disease": r.suspected_disease}, district=r.district, taluka=r.taluka, owner_id=r.user_id).publish()
    return serialize_report(r)
