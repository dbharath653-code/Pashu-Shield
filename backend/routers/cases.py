import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (DiseaseReport, DispatchRequest, LabSample, User, UserRole, VeterinarianProfile, VeterinaryCase,
                            VeterinaryVisit, WorkflowEvent)
from backend.schemas import CaseAssignRequest, CaseStatusUpdate, DispatchResponse, VetLocationUpdate, VetProfileUpdate, VisitCreate
from backend.security import (VET_ROLES, Permission, ensure_can_access_record, forbidden, in_jurisdiction, jurisdiction_scope,
                              require_permission, resolve_district_filter)
from backend.services import routing_service
from backend.services.audit_service import AuditService
from backend.services.dispatch_service import DispatchEngine
from backend.services.events import Event
from backend.services.notification_service import NotificationService
from backend.services.workflow import normalize_status, transition

router = APIRouter(prefix="/cases", tags=["Veterinary Cases & Dispatch"])

_TS = {"ACCEPTED": "accepted_at", "EN_ROUTE": "en_route_at", "ON_SITE": "on_site_at", "RESOLVED": "resolved_at", "CLOSED": "closed_at"}
_REPORT_FOR_CASE = {"ON_SITE": "VISITED", "RESOLVED": "RESOLVED", "CLOSED": "CLOSED"}


def serialize_case(c: VeterinaryCase) -> dict:
    return {
        "id": c.id, "caseNumber": c.case_number, "reportId": c.report_id, "animalHerdId": c.animal_id or c.herd_id,
        "species": c.species, "location": f"{c.village}, {c.district}", "district": c.district, "village": c.village,
        "lat": c.lat, "lng": c.lng, "locationStatus": "GPS_OR_USER_ENTERED" if c.lat is not None else "LOCATION_UNAVAILABLE",
        "reportedProblem": c.reported_problem, "riskScore": c.risk_score, "priority": c.priority,
        "reportedAt": c.created_at.strftime("%d %b %Y, %I:%M %p") if c.created_at else None,
        "assignedVet": c.assigned_vet_id, "status": c.status, "diagnosis": c.diagnosis, "treatmentPrescribed": c.treatment_prescribed,
        "requiresLab": c.requires_lab, "version": c.version, "isDemo": c.is_demo, "syncStatus": "Synced",
    }


def _vet_can_act(user: User, case: VeterinaryCase) -> None:
    if user.role in VET_ROLES and case.assigned_vet_id != user.id:
        raise forbidden("This case is not assigned to you", code="NOT_ASSIGNED")


@router.get("")
async def get_cases(status: Optional[str] = None, priority: Optional[str] = None, district: Optional[str] = None,
                    limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
                    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.CASE_READ))):
    stmt = select(VeterinaryCase).where(VeterinaryCase.deleted_at.is_(None))
    if current_user.role == UserRole.FARMER.value:
        stmt = stmt.where(VeterinaryCase.farmer_id == current_user.id)
    elif current_user.role in VET_ROLES:
        stmt = stmt.where((VeterinaryCase.assigned_vet_id == current_user.id) | ((VeterinaryCase.district == current_user.district) & (VeterinaryCase.assigned_vet_id.is_(None))))
    else:
        d = resolve_district_filter(current_user, district)
        if d:
            stmt = stmt.where(VeterinaryCase.district == d)
        if jurisdiction_scope(current_user)["taluka"]:
            stmt = stmt.where(VeterinaryCase.taluka == current_user.taluka)
    if status:
        stmt = stmt.where(VeterinaryCase.status == normalize_status(status))
    if priority:
        stmt = stmt.where(VeterinaryCase.priority == priority)
    rows = (await db.execute(stmt.order_by(VeterinaryCase.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    return [serialize_case(c) for c in rows]


# --- Vet self-service (declared before /{case_id} routes) ---------------------------------
@router.get("/dispatch/mine")
async def my_dispatch_requests(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VET_PROFILE_UPDATE))):
    rows = (await db.execute(select(DispatchRequest).where(DispatchRequest.vet_id == current_user.id, DispatchRequest.status == "PENDING").order_by(DispatchRequest.created_at.desc()))).scalars().all()
    return [{"id": d.id, "caseId": d.case_id, "expiresAt": d.expires_at.isoformat(), "distanceKm": d.distance_km, "distanceBasis": d.distance_basis, "etaStatus": d.eta_status} for d in rows]


@router.put("/vet/profile")
async def update_vet_profile(req: VetProfileUpdate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VET_PROFILE_UPDATE))):
    p = await db.get(VeterinarianProfile, current_user.id)
    if p is None:
        p = VeterinarianProfile(user_id=current_user.id)
        db.add(p)
    for k, v in req.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    await AuditService.for_user(db, current_user, "VET_PROFILE_UPDATED", "VET_PROFILE", current_user.id, request=request, commit=False, new_value=req.model_dump(exclude_none=True))
    await db.commit()
    return {"success": True, "availability_status": p.availability_status}


@router.put("/vet/location")
async def update_vet_location(req: VetLocationUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VET_PROFILE_UPDATE))):
    p = await db.get(VeterinarianProfile, current_user.id)
    if p is None:
        p = VeterinarianProfile(user_id=current_user.id)
        db.add(p)
    p.current_lat, p.current_lng, p.location_accuracy_m, p.last_location_update = req.lat, req.lng, req.accuracy_m, datetime.utcnow()
    await db.commit()
    return {"success": True, "last_location_update": p.last_location_update.isoformat()}


# --- Case detail & lifecycle ----------------------------------------------------------------
async def _load(db: AsyncSession, case_id: str) -> VeterinaryCase:
    c = await db.get(VeterinaryCase, case_id)
    if c is None or c.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
    return c


@router.get("/{case_id}")
async def get_case_details(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.CASE_READ))):
    c = await _load(db, case_id)
    ensure_can_access_record(current_user, owner_ids=[c.farmer_id], district=c.district, taluka=c.taluka, assigned_vet_id=c.assigned_vet_id)
    visits = (await db.execute(select(VeterinaryVisit).where(VeterinaryVisit.case_id == case_id).order_by(VeterinaryVisit.visit_date.desc()))).scalars().all()
    samples = (await db.execute(select(LabSample).where(LabSample.case_id == case_id))).scalars().all()
    history = (await db.execute(select(WorkflowEvent).where(WorkflowEvent.entity_type == "CASE", WorkflowEvent.entity_id == case_id).order_by(WorkflowEvent.created_at))).scalars().all()
    return {**serialize_case(c),
            "visits": [{"id": v.id, "visitDate": v.visit_date.isoformat(), "observations": v.observations, "treatmentGiven": v.treatment_given, "followUpNeeded": v.follow_up_needed} for v in visits],
            "samples": [{"id": s.id, "sampleCode": s.sample_code, "status": s.status, "disease": s.disease_suspected} for s in samples],
            "history": [{"from": h.from_status, "to": h.to_status, "at": h.created_at.isoformat(), "actor": h.actor_id, "note": h.note} for h in history]}


@router.patch("/{case_id}/status")
async def update_case_status(case_id: str, req: CaseStatusUpdate, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    c = await _load(db, case_id)
    ensure_can_access_record(current_user, district=c.district, taluka=c.taluka, assigned_vet_id=c.assigned_vet_id)
    _vet_can_act(current_user, c)
    if req.expected_version is not None and req.expected_version != c.version:
        raise HTTPException(status_code=409, detail={"code": "VERSION_CONFLICT", "message": f"Case was modified (server version {c.version})"})
    old = c.status
    new = transition(db, "CASE", c, req.status, current_user, note=req.notes)
    if new == "ACCEPTED":
        # Accepting via the status endpoint also resolves the pending dispatch offer.
        pending = (await db.execute(select(DispatchRequest).where(DispatchRequest.case_id == c.id, DispatchRequest.vet_id == current_user.id, DispatchRequest.status == "PENDING"))).scalars().first()
        if pending:
            pending.status, pending.responded_at = "ACCEPTED", datetime.utcnow()
    now = datetime.utcnow()
    if new in _TS and getattr(c, _TS[new]) is None:
        setattr(c, _TS[new], now)
    if req.diagnosis:
        c.diagnosis = req.diagnosis
    if req.treatment_prescribed:
        c.treatment_prescribed = req.treatment_prescribed
    c.updated_by = current_user.id
    if c.report_id and new in _REPORT_FOR_CASE:
        rep = await db.get(DiseaseReport, c.report_id)
        from backend.services.workflow import can_transition
        if rep and can_transition("REPORT", rep.status, _REPORT_FOR_CASE[new]):
            transition(db, "REPORT", rep, _REPORT_FOR_CASE[new], current_user, note=f"case {c.case_number} -> {new}")
    if c.farmer_id:
        farmer = await db.get(User, c.farmer_id)
        await NotificationService.queue(db, channel="IN_APP", template="CASE_STATUS_UPDATED", context={"case_number": c.case_number, "status": new}, user=farmer)
    await AuditService.for_user(db, current_user, "CASE_STATUS_CHANGED", "CASE", c.id, request=request, commit=False, old_value={"status": old}, new_value={"status": new})
    await db.commit()
    await Event("case.status_changed", {"id": c.id, "caseNumber": c.case_number, "status": new, "updatedBy": current_user.full_name}, district=c.district, taluka=c.taluka, owner_id=c.farmer_id, user_ids=[c.assigned_vet_id] if c.assigned_vet_id else []).publish()
    return {"message": "Case status updated successfully", "case": serialize_case(c)}


@router.post("/{case_id}/accept")
async def accept_dispatch(case_id: str, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    c = await _load(db, case_id)
    pending = (await db.execute(select(DispatchRequest).where(DispatchRequest.case_id == case_id, DispatchRequest.vet_id == current_user.id, DispatchRequest.status == "PENDING"))).scalars().first()
    if not pending or c.assigned_vet_id != current_user.id:
        raise HTTPException(status_code=409, detail={"code": "NO_PENDING_OFFER", "message": "There is no pending dispatch offer for you on this case"})
    if pending.expires_at < datetime.utcnow():
        raise HTTPException(status_code=409, detail={"code": "OFFER_EXPIRED", "message": "Dispatch offer has expired"})
    pending.status, pending.responded_at = "ACCEPTED", datetime.utcnow()
    transition(db, "CASE", c, "ACCEPTED", current_user)
    c.accepted_at = datetime.utcnow()
    eta = await routing_service.route(*(await _vet_origin(db, current_user.id)), c.lat, c.lng)
    pending.eta_status, pending.eta_minutes = eta["eta_status"], eta["eta_minutes"]
    await AuditService.for_user(db, current_user, "DISPATCH_ACCEPTED", "CASE", c.id, request=request, commit=False)
    await db.commit()
    await Event("vet.accepted", {"caseId": c.id, "vetId": current_user.id, "eta": eta}, district=c.district, owner_id=c.farmer_id).publish()
    return {"case": serialize_case(c), "eta": eta}


async def _vet_origin(db: AsyncSession, vet_id: str):
    p = await db.get(VeterinarianProfile, vet_id)
    return (p.current_lat, p.current_lng) if p else (None, None)


@router.post("/{case_id}/reject")
async def reject_dispatch(case_id: str, req: DispatchResponse, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    c = await _load(db, case_id)
    pending = (await db.execute(select(DispatchRequest).where(DispatchRequest.case_id == case_id, DispatchRequest.vet_id == current_user.id, DispatchRequest.status == "PENDING"))).scalars().first()
    if not pending:
        raise HTTPException(status_code=409, detail={"code": "NO_PENDING_OFFER", "message": "There is no pending dispatch offer for you on this case"})
    pending.status, pending.responded_at, pending.reject_reason = "REJECTED", datetime.utcnow(), req.reason
    transition(db, "CASE", c, "REJECTED", current_user, note=req.reason)
    nxt = await DispatchEngine.offer_next(db, c, current_user)
    await AuditService.for_user(db, current_user, "DISPATCH_REJECTED", "CASE", c.id, request=request, commit=False, new_value={"reason": req.reason, "reoffered_to": nxt["vet_id"] if nxt else None})
    await db.commit()
    await Event("vet.rejected", {"caseId": c.id, "vetId": current_user.id, "reofferedTo": nxt["vet_id"] if nxt else None}, district=c.district, user_ids=[nxt["vet_id"]] if nxt else []).publish()
    return {"case": serialize_case(c), "reoffered_to": nxt["vet_id"] if nxt else None}


@router.post("/{case_id}/assign")
async def manual_assign(case_id: str, req: CaseAssignRequest, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VET_DISPATCH))):
    c = await _load(db, case_id)
    ensure_can_access_record(current_user, district=c.district, taluka=c.taluka)
    vet = await db.get(User, req.vet_id)
    if not vet or vet.role not in VET_ROLES or not vet.is_active or not vet.is_verified:
        raise HTTPException(status_code=422, detail={"code": "INVALID_VET", "message": "Target user is not an active, verified veterinarian"})
    if not in_jurisdiction(current_user, vet.district):
        raise forbidden("Veterinarian is outside your jurisdiction", code="OUT_OF_JURISDICTION")
    for d in (await db.execute(select(DispatchRequest).where(DispatchRequest.case_id == case_id, DispatchRequest.status == "PENDING"))).scalars().all():
        d.status = "CANCELLED"
    await DispatchEngine.create_request(db, c, {"vet_id": vet.id, "distance_basis": "MANUAL"})
    c.assigned_vet_id, c.assigned_at = vet.id, datetime.utcnow()
    transition(db, "CASE", c, "ASSIGNED", current_user, note="manual assignment")
    await NotificationService.queue(db, channel="SMS", template="VETERINARIAN_ASSIGNED", context={"case_number": c.case_number}, user=vet, dedup_key=f"vet-assigned:{c.id}:{vet.id}", require_consent=False)
    await AuditService.for_user(db, current_user, "CASE_MANUALLY_ASSIGNED", "CASE", c.id, request=request, commit=False, new_value={"vet_id": vet.id})
    await db.commit()
    await Event("vet.assigned", {"caseId": c.id, "vetId": vet.id}, district=c.district, user_ids=[vet.id]).publish()
    return serialize_case(c)


@router.get("/{case_id}/candidates")
async def dispatch_candidates(case_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.VET_DISPATCH))):
    c = await _load(db, case_id)
    ensure_can_access_record(current_user, district=c.district, taluka=c.taluka)
    return await DispatchEngine.find_eligible_veterinarians(db, c.district, c.lat, c.lng, species=c.species)


@router.post("/{case_id}/visits")
async def log_case_visit(case_id: str, req: VisitCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    c = await _load(db, case_id)
    _vet_can_act(current_user, c)
    ensure_can_access_record(current_user, district=c.district, assigned_vet_id=c.assigned_vet_id)
    visit = VeterinaryVisit(id=f"VIS-{uuid.uuid4().hex[:10].upper()}", case_id=case_id, vet_id=current_user.id, observations=req.observations,
                            treatment_given=req.treatment_given, follow_up_needed=req.follow_up_needed, follow_up_date=req.follow_up_date)
    db.add(visit)
    if req.request_sample:
        c.requires_lab = True
    await AuditService.for_user(db, current_user, "VISIT_LOGGED", "CASE", c.id, request=request, commit=False)
    await db.commit()
    return {"message": "Visit logged successfully", "visit_id": visit.id}
