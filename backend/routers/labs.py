import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (CustodyEvent, DiseaseReport, LabResultRevision, LabSample, LabTest, SurveillanceObservation, User,
                            UserRole, VeterinaryCase)
from backend.schemas import CustodyEventCreate, SampleCreate, SampleStatusUpdate, SampleVerificationRequest, TestResultUpdate
from backend.security import LAB_ROLES, VET_ROLES, Permission, ensure_can_access_record, forbidden, require_permission, resolve_district_filter
from backend.services.alert_engine import raise_alert
from backend.services.audit_service import AuditService
from backend.services.events import Event
from backend.services.lab_integration import get_lab_provider
from backend.services.notification_service import NotificationService
from backend.services.workflow import can_transition, normalize_status, transition

router = APIRouter(prefix="/labs", tags=["Laboratory Management"])


def _can_see_sample(user: User, s: LabSample) -> None:
    if user.role in LAB_ROLES or user.role == UserRole.SYSTEM_ADMIN.value:
        return
    ensure_can_access_record(user, owner_ids=[s.collected_by_id, s.farmer_id], district=s.district)


def serialize_sample(s: LabSample, tests=None) -> dict:
    return {
        "id": s.id, "sampleCode": s.sample_code, "caseId": s.case_id, "animalId": s.animal_id, "species": s.species,
        "diseaseSuspected": s.disease_suspected, "sampleType": s.sample_type, "priority": s.priority, "status": s.status,
        "collectionDate": s.collection_date.strftime("%Y-%m-%d") if s.collection_date else None, "district": s.district,
        "location": s.location, "qrCode": s.qr_code, "finalResult": s.final_result, "verifiedBy": s.verified_by_name,
        "verificationRemarks": s.verification_remarks, "releasedAt": s.released_at.isoformat() if s.released_at else None,
        "externalLimsId": s.external_lims_id, "version": s.version, "isDemo": s.is_demo,
        "tests": [{"id": t.id, "testName": t.test_name, "status": t.status, "result": t.result, "value": t.value, "remarks": t.remarks, "resultVersion": t.result_version} for t in (tests or [])],
    }


@router.get("/samples")
async def get_lab_samples(status: Optional[str] = None, district: Optional[str] = None, priority: Optional[str] = None,
                          limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
                          db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.LAB_SAMPLE_READ))):
    stmt = select(LabSample).where(LabSample.deleted_at.is_(None))
    if current_user.role in VET_ROLES:
        stmt = stmt.where((LabSample.collected_by_id == current_user.id) | (LabSample.district == current_user.district))
    elif current_user.role not in LAB_ROLES:
        d = resolve_district_filter(current_user, district)
        if d:
            stmt = stmt.where(LabSample.district == d)
    if district and current_user.role in LAB_ROLES:
        stmt = stmt.where(LabSample.district == district)
    if status:
        stmt = stmt.where(LabSample.status == normalize_status(status))
    if priority:
        stmt = stmt.where(LabSample.priority == priority)
    samples = (await db.execute(stmt.order_by(LabSample.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    ids = [s.id for s in samples]
    tests_by = {}
    if ids:
        for t in (await db.execute(select(LabTest).where(LabTest.sample_id.in_(ids)))).scalars().all():  # single query, no N+1
            tests_by.setdefault(t.sample_id, []).append(t)
    return [serialize_sample(s, tests_by.get(s.id, [])) for s in samples]


async def create_sample(db: AsyncSession, req: SampleCreate, user: User, request=None) -> LabSample:
    if req.case_id:
        case = await db.get(VeterinaryCase, req.case_id)
        if not case:
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})
        ensure_can_access_record(user, district=case.district, assigned_vet_id=case.assigned_vet_id)
    code = f"MH-{req.district[:3].upper()}-{datetime.utcnow():%y%m}-{uuid.uuid4().hex[:6].upper()}"
    s = LabSample(id=req.id or f"SMP-{uuid.uuid4().hex[:10].upper()}", sample_code=code, case_id=req.case_id, animal_id=req.animal_id,
                  collected_by_id=user.id, lab_id=req.lab_id, species=req.species, disease_suspected=req.disease_suspected,
                  sample_type=req.sample_type, priority=req.priority, status="COLLECTED", district=req.district, location=req.location,
                  collection_lat=req.lat, collection_lng=req.lng, qr_code=f"PS:{code}", notes=req.notes, is_demo=bool(user.is_demo),
                  updated_by=user.id)
    db.add(s)
    db.add(CustodyEvent(id=uuid.uuid4().hex, sample_id=s.id, event_type="COLLECTED", actor_id=user.id, transfer_from=None, transfer_to=user.full_name,
                        condition="GOOD", lat=req.lat, lng=req.lng, location_label=req.location))
    for name in req.tests:
        db.add(LabTest(id=f"TST-{uuid.uuid4().hex[:10].upper()}", sample_id=s.id, test_name=name[:128], status="Pending"))
    if req.case_id:
        case = await db.get(VeterinaryCase, req.case_id)
        case.requires_lab = True
        if case.report_id:
            rep = await db.get(DiseaseReport, case.report_id)
            if rep and can_transition("REPORT", rep.status, "SAMPLE_COLLECTED"):
                transition(db, "REPORT", rep, "SAMPLE_COLLECTED", user)
    push = await get_lab_provider().register_sample({"sample_code": code, "species": req.species, "disease": req.disease_suspected, "type": req.sample_type})
    s.external_lims_id = push.get("external_id")
    await AuditService.for_user(db, user, "SAMPLE_REGISTERED", "LAB_SAMPLE", s.id, request=request, commit=False, new_value={"sample_code": code, "lims": push.get("status")})
    return s


@router.post("/samples")
async def register_lab_sample(req: SampleCreate, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.LAB_SAMPLE_CREATE))):
    s = await create_sample(db, req, current_user, request)
    await db.commit()
    await Event("sample.collected", {"id": s.id, "sampleCode": s.sample_code, "district": s.district, "disease": s.disease_suspected}, district=s.district).publish()
    return {"message": "Sample registered successfully", "sample_id": s.id, "sample_code": s.sample_code, "qr_code": s.qr_code, "lims_integration": get_lab_provider().status}


async def _load(db, sample_id) -> LabSample:
    s = await db.get(LabSample, sample_id)
    if s is None or s.deleted_at is not None:
        raise HTTPException(status_code=404, detail={"code": "SAMPLE_NOT_FOUND", "message": "Sample not found"})
    return s


@router.get("/samples/{sample_id}/custody")
async def get_custody(sample_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.LAB_SAMPLE_READ))):
    s = await _load(db, sample_id)
    _can_see_sample(current_user, s)
    rows = (await db.execute(select(CustodyEvent).where(CustodyEvent.sample_id == sample_id).order_by(CustodyEvent.occurred_at))).scalars().all()
    return [{"id": e.id, "eventType": e.event_type, "actor": e.actor_id, "from": e.transfer_from, "to": e.transfer_to, "condition": e.condition,
             "transportStatus": e.transport_status, "temperatureC": e.temperature_c, "location": e.location_label, "lat": e.lat, "lng": e.lng,
             "occurredAt": e.occurred_at.isoformat(), "recordedAt": e.recorded_at.isoformat(), "notes": e.notes} for e in rows]


@router.post("/samples/{sample_id}/custody")
async def add_custody_event(sample_id: str, req: CustodyEventCreate, request: Request, db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_permission(Permission.LAB_SAMPLE_READ))):
    s = await _load(db, sample_id)
    _can_see_sample(current_user, s)
    if req.event_type in ("IN_TRANSIT", "RECEIVED"):
        target = req.event_type
        if target == "RECEIVED" and current_user.role not in LAB_ROLES and current_user.role != UserRole.SYSTEM_ADMIN.value:
            raise forbidden("Only laboratory staff can receive samples")
        transition(db, "SAMPLE", s, target, current_user, note=req.notes)
        if target == "RECEIVED":
            s.received_at = datetime.utcnow()
    db.add(CustodyEvent(id=uuid.uuid4().hex, sample_id=s.id, actor_id=current_user.id, recorded_at=datetime.utcnow(),
                        occurred_at=(req.occurred_at.replace(tzinfo=None) if req.occurred_at else datetime.utcnow()),
                        **req.model_dump(exclude={"occurred_at"})))
    await AuditService.for_user(db, current_user, f"CUSTODY_{req.event_type}", "LAB_SAMPLE", s.id, request=request, commit=False, new_value=req.model_dump(mode="json", exclude_none=True))
    await db.commit()
    return {"success": True, "status": s.status}


_SAMPLE_PERMS = {"RECEIVED": Permission.LAB_SAMPLE_PROCESS, "ACCEPTED": Permission.LAB_SAMPLE_PROCESS, "REJECTED": Permission.LAB_SAMPLE_PROCESS,
                 "TESTING": Permission.LAB_SAMPLE_PROCESS, "RESULT_PENDING": Permission.LAB_RESULT_ENTER, "VERIFIED": Permission.LAB_RESULT_VERIFY,
                 "RELEASED": Permission.LAB_RESULT_VERIFY, "CLOSED": Permission.LAB_SAMPLE_PROCESS}


@router.patch("/samples/{sample_id}/status")
async def update_sample_status(sample_id: str, req: SampleStatusUpdate, request: Request, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_permission(Permission.LAB_SAMPLE_READ))):
    from backend.security import has_permission
    s = await _load(db, sample_id)
    _can_see_sample(current_user, s)
    target = normalize_status(req.status)
    needed = _SAMPLE_PERMS.get(target)
    if needed and not has_permission(current_user, needed):
        raise forbidden(f"Missing permission: {needed.value}")
    if target == "VERIFIED":
        raise HTTPException(status_code=422, detail={"code": "USE_VERIFY_ENDPOINT", "message": "Use POST /labs/samples/{id}/verify to verify results"})
    old = s.status
    # Legacy UI jumps (e.g. COLLECTED -> TESTING) are walked through the intermediate states so
    # the custody/audit trail stays complete, but only along valid edges.
    path = {"TESTING": ["RECEIVED", "ACCEPTED", "TESTING"]}.get(target, [target])
    for step in path:
        if normalize_status(s.status) == step:
            continue
        if not can_transition("SAMPLE", s.status, step) and step != target:
            continue
        transition(db, "SAMPLE", s, step, current_user, note=req.notes)
        if step == "RECEIVED":
            s.received_at = datetime.utcnow()
            db.add(CustodyEvent(id=uuid.uuid4().hex, sample_id=s.id, event_type="RECEIVED", actor_id=current_user.id, transfer_to=current_user.full_name, condition=req.condition, temperature_c=req.temperature_c))
    if target == "TESTING":
        s.tested_at = datetime.utcnow()
    if target == "REJECTED":
        s.rejection_reason = req.rejection_reason or req.notes
        db.add(CustodyEvent(id=uuid.uuid4().hex, sample_id=s.id, event_type="REJECTED", actor_id=current_user.id, condition=req.condition, notes=s.rejection_reason))
    if target == "IN_TRANSIT":
        db.add(CustodyEvent(id=uuid.uuid4().hex, sample_id=s.id, event_type="IN_TRANSIT", actor_id=current_user.id, transfer_to=req.transfer_to, condition=req.condition, temperature_c=req.temperature_c))
    if s.case_id and target == "TESTING":
        case = await db.get(VeterinaryCase, s.case_id)
        rep = await db.get(DiseaseReport, case.report_id) if case and case.report_id else None
        if rep and can_transition("REPORT", rep.status, "LAB_TESTING"):
            transition(db, "REPORT", rep, "LAB_TESTING", current_user)
    await AuditService.for_user(db, current_user, "SAMPLE_STATUS_CHANGED", "LAB_SAMPLE", s.id, request=request, commit=False, old_value={"status": old}, new_value={"status": s.status})
    await db.commit()
    await Event("sample.status_changed", {"id": s.id, "status": s.status, "updated_by": current_user.full_name}, district=s.district).publish()
    return {"message": "Sample status updated", "status": s.status}


@router.patch("/samples/{sample_id}/tests")
async def update_sample_test(sample_id: str, req: TestResultUpdate, request: Request, db: AsyncSession = Depends(get_db),
                             current_user: User = Depends(require_permission(Permission.LAB_RESULT_ENTER))):
    s = await _load(db, sample_id)
    test = (await db.execute(select(LabTest).where(LabTest.id == req.test_id, LabTest.sample_id == sample_id))).scalars().first()
    if not test:
        raise HTTPException(status_code=404, detail={"code": "TEST_NOT_FOUND", "message": "Test not found"})
    if normalize_status(s.status) in ("VERIFIED", "RELEASED") and not req.correction_reason:
        raise HTTPException(status_code=409, detail={"code": "CORRECTION_REASON_REQUIRED", "message": "Result already verified; corrections need correction_reason"})
    test.result_version = (test.result_version or 0) + 1
    db.add(LabResultRevision(id=uuid.uuid4().hex, test_id=test.id, version=test.result_version, result=req.result, value=req.value, remarks=req.remarks,
                             entered_by_id=current_user.id, correction_reason=req.correction_reason))
    test.status, test.result, test.value, test.remarks = req.status, req.result, req.value, req.remarks
    test.tested_by_id, test.tested_at = current_user.id, datetime.utcnow()
    if req.correction_reason and normalize_status(s.status) in ("VERIFIED", "RELEASED"):
        transition(db, "SAMPLE", s, "RESULT_PENDING", current_user, note=f"correction: {req.correction_reason}")
        s.verified_at = s.verified_by_id = s.verified_by_name = None
    elif req.status == "Completed" and normalize_status(s.status) == "TESTING":
        transition(db, "SAMPLE", s, "RESULT_PENDING", current_user)
        if s.case_id:
            case = await db.get(VeterinaryCase, s.case_id)
            rep = await db.get(DiseaseReport, case.report_id) if case and case.report_id else None
            if rep and can_transition("REPORT", rep.status, "RESULT_AVAILABLE"):
                transition(db, "REPORT", rep, "RESULT_AVAILABLE", current_user)
    await AuditService.for_user(db, current_user, "LAB_RESULT_ENTERED" if not req.correction_reason else "LAB_RESULT_CORRECTED", "LAB_TEST", test.id, request=request, commit=False,
                                new_value={"result": req.result, "version": test.result_version})
    await db.commit()
    await Event("lab.result_available", {"id": s.id, "sampleCode": s.sample_code, "status": s.status}, district=s.district).publish()
    return {"message": "Test result recorded", "test_id": test.id, "result": test.result, "result_version": test.result_version, "sample_status": s.status}


@router.post("/samples/{sample_id}/verify")
async def verify_sample_result(sample_id: str, req: SampleVerificationRequest, request: Request, db: AsyncSession = Depends(get_db),
                               current_user: User = Depends(require_permission(Permission.LAB_RESULT_VERIFY))):
    s = await _load(db, sample_id)
    tests = (await db.execute(select(LabTest).where(LabTest.sample_id == s.id))).scalars().all()
    # Compatibility: older UI verifies straight from TESTING; allow only if every test has a result.
    if normalize_status(s.status) == "TESTING":
        if tests and any(t.result is None for t in tests) and not req.final_result:
            raise HTTPException(status_code=409, detail={"code": "RESULTS_INCOMPLETE", "message": "All tests need a result (or supply final_result) before verification"})
        transition(db, "SAMPLE", s, "RESULT_PENDING", current_user)
    transition(db, "SAMPLE", s, "VERIFIED", current_user, note=req.remarks)
    final = req.final_result or ("POSITIVE" if any((t.result or "").lower() == "positive" for t in tests) else ("NEGATIVE" if tests and all((t.result or "").lower() == "negative" for t in tests) else "INCONCLUSIVE"))
    s.final_result = final
    s.verified_at, s.verified_by_id, s.verified_by_name, s.verification_remarks = datetime.utcnow(), current_user.id, current_user.full_name, req.remarks
    # Release to surveillance
    transition(db, "SAMPLE", s, "RELEASED", current_user)
    s.released_at = datetime.utcnow()
    rep = None
    if s.case_id:
        case = await db.get(VeterinaryCase, s.case_id)
        rep = await db.get(DiseaseReport, case.report_id) if case and case.report_id else None
        if rep:
            if can_transition("REPORT", rep.status, "RESULT_AVAILABLE") and normalize_status(rep.status) == "LAB_TESTING":
                transition(db, "REPORT", rep, "RESULT_AVAILABLE", current_user)
            if final == "POSITIVE":
                rep.verification_status = "LAB_CONFIRMED"
            if can_transition("REPORT", rep.status, "VERIFIED") and normalize_status(rep.status) == "RESULT_AVAILABLE":
                transition(db, "REPORT", rep, "VERIFIED", current_user, note=f"lab {final}")
    if final == "POSITIVE":
        db.add(SurveillanceObservation(id=uuid.uuid4().hex, disease=s.disease_suspected, species=s.species, district=s.district,
                                       lat=(rep.lat if rep else s.collection_lat), lng=(rep.lng if rep else s.collection_lng),
                                       case_count=(rep.number_affected if rep else 1), death_count=(rep.number_dead if rep else 0),
                                       observed_at=s.collection_date or datetime.utcnow(), source_type="LAB", source_name="PASHU_SHIELD_LAB",
                                       source_record_id=s.id, verification_status="VERIFIED", confidence=1.0, is_demo=s.is_demo))
        await raise_alert(db, alert_type="LAB_RESULT", severity="CRITICAL", title=f"Lab-confirmed {s.disease_suspected} – {s.district}",
                          message=f"Sample {s.sample_code} verified POSITIVE for {s.disease_suspected}.", dedup_key=f"lab:{s.id}:positive",
                          district=s.district, disease=s.disease_suspected, related_entity_type="SAMPLE", related_entity_id=s.id,
                          evidence_level="LAB_CONFIRMED", is_demo=s.is_demo)
    if rep and rep.user_id:
        farmer = await db.get(User, rep.user_id)
        if farmer:
            await NotificationService.queue(db, channel="IN_APP", template="LAB_RESULT_READY", context={"sample_code": s.sample_code}, user=farmer)
    await AuditService.for_user(db, current_user, "LAB_RESULT_VERIFIED", "LAB_SAMPLE", s.id, request=request, commit=False, new_value={"status": s.status, "final_result": final, "remarks": req.remarks})
    await db.commit()
    await Event("lab.result_verified", {"id": s.id, "sampleCode": s.sample_code, "disease": s.disease_suspected, "district": s.district, "finalResult": final, "verified_by": current_user.full_name}, district=s.district, owner_id=rep.user_id if rep else None).publish()
    return {"message": "Lab result verified and released to surveillance system", "sample_id": s.id, "final_result": final, "status": s.status}
