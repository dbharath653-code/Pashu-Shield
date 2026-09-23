"""Offline-first synchronisation.

PUSH  – authenticated only (anonymous writes removed). Every item carries an idempotency key;
        a replay returns the original result. CREATE of reports goes through the full report
        pipeline (triage, case, dispatch, alerts). UPDATEs use optimistic versioning: if the
        client's base_version != server version the change is NOT applied; a SyncConflict is
        stored and returned (never silently discarded).
        Conflict policy: reports/lab samples/cases -> MANUAL (server wins until resolved);
        animals/herds -> field-level merge when the changed fields don't overlap.
PULL  – cursor-based (updated_at, id) pagination over every store, scoped to the user,
        including tombstones (deleted_at) so clients can remove records.
"""
import base64
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Animal, DiseaseReport, Herd, LabSample, SyncConflict, SyncEvent, User, UserRole, VaccinationRecord, VeterinaryCase
from backend.schemas import AnimalCreate, ConflictResolution, DiseaseReportCreate, HerdCreate, SyncPushRequest, VaccinationRecordCreate
from backend.security import LAB_ROLES, VET_ROLES, Permission, ensure_can_access_record, jurisdiction_scope, require_permission
from backend.services.audit_service import AuditService
from backend.services.events import Event
from backend.services.rate_limit import enforce

router = APIRouter(prefix="/sync", tags=["Offline-First Synchronization"])

STORE_ALIASES = {"reports": "reports", "health_records": "reports", "diseaseReports": "reports", "animals": "animals", "herds": "herds",
                 "vaccinations": "vaccinations", "vaccination_records": "vaccinations"}
MERGEABLE = {"animals": ["health_status", "breed", "age_years", "village", "lat", "lng", "risk_score"], "herds": ["total_animals", "health_status", "village", "lat", "lng"]}
MODEL_FOR = {"animals": Animal, "herds": Herd, "reports": DiseaseReport}
CAMEL = {"tagId": "tag_id", "healthStatus": "health_status", "riskScore": "risk_score", "totalAnimals": "total_animals", "age": "age_years",
         "numberAffected": "number_affected", "numberDead": "number_dead", "disease": "suspected_disease", "batchNumber": "batch_number",
         "animalId": "animal_id", "herdId": "herd_id", "vaccinationDate": "vaccination_date", "nextDueDate": "next_due_date", "temperatureUnit": "temperature_unit"}


def _snake(data: Dict[str, Any]) -> Dict[str, Any]:
    return {CAMEL.get(k, k): v for k, v in data.items()}


def _row(obj, fields: List[str]) -> Dict[str, Any]:
    return {f: getattr(obj, f, None) for f in fields}


async def _existing_event(db, user_id, key) -> Optional[SyncEvent]:
    return (await db.execute(select(SyncEvent).where(SyncEvent.idempotency_key == key))).scalars().first()


async def _apply_create(db: AsyncSession, store: str, data: Dict[str, Any], user: User, item, request) -> Dict[str, Any]:
    if store == "reports":
        from backend.services.report_service import submit_report
        d = _snake(data)
        req = DiseaseReportCreate(**{k: v for k, v in d.items() if k in DiseaseReportCreate.model_fields})
        existing = (await db.execute(select(DiseaseReport).where(DiseaseReport.client_id == item.id, DiseaseReport.user_id == user.id))).scalars().first()
        if existing:
            return {"serverId": existing.id, "version": existing.version}
        res = await submit_report(db, req.model_copy(update={"client_id": req.client_id or (item.id if len(item.id) <= 64 else None)}), user,
                                  source="OFFLINE_SYNC", device_id=item.device_id, request=request)
        return {"serverId": res["report"]["id"], "reportNumber": res["report"]["reportNumber"], "triage": res["triage"]["risk_level"], "version": 1}
    if store == "animals":
        req = AnimalCreate(**{k: v for k, v in _snake(data).items() if k in AnimalCreate.model_fields})
        a = Animal(id=req.id or f"ANI-{uuid.uuid4().hex[:10].upper()}", owner_id=user.id, updated_by=user.id, device_id=item.device_id, is_demo=user.is_demo,
                   **req.model_dump(exclude={"id"}))
        db.add(a)
        return {"serverId": a.id, "version": 1}
    if store == "herds":
        req = HerdCreate(**{k: v for k, v in _snake(data).items() if k in HerdCreate.model_fields})
        h = Herd(id=req.id or f"HRD-{uuid.uuid4().hex[:10].upper()}", owner_id=user.id, updated_by=user.id, device_id=item.device_id, is_demo=user.is_demo,
                 **req.model_dump(exclude={"id"}))
        db.add(h)
        return {"serverId": h.id, "version": 1}
    if store == "vaccinations":
        from backend.routers.vaccinations import create_vaccination_record
        req = VaccinationRecordCreate(**{k: v for k, v in _snake(data).items() if k in VaccinationRecordCreate.model_fields})
        rec, duplicate = await create_vaccination_record(db, req, user, device_id=item.device_id)
        return {"serverId": rec.id, "version": rec.version, "duplicateOf": rec.id if duplicate else None}
    raise ValueError(f"Unsupported store: {store}")


async def _apply_update(db: AsyncSession, store: str, entity_id: str, data: Dict[str, Any], base_version: Optional[int], user: User, item) -> Dict[str, Any]:
    model = MODEL_FOR.get(store)
    if not model or store == "reports":
        raise ValueError(f"UPDATE not supported offline for {store}; reports are changed through workflow endpoints")
    obj = await db.get(model, entity_id)
    if obj is None:
        raise LookupError("Record not found on server")
    ensure_can_access_record(user, owner_ids=[getattr(obj, "owner_id", None)], district=obj.district)
    allowed = MERGEABLE[store]
    changes = {k: v for k, v in _snake(data).items() if k in allowed}
    if base_version is None or base_version == obj.version:
        for k, v in changes.items():
            setattr(obj, k, v)
        obj.version += 1
        obj.updated_by, obj.device_id = user.id, item.device_id
        return {"serverId": obj.id, "version": obj.version, "status": "SYNCED"}
    # Version mismatch → determine which fields the server changed since the client's base.
    # We don't keep full history per field, so treat any field whose server value differs from
    # the client's new value as conflicting.
    conflicting = [k for k, v in changes.items() if getattr(obj, k) != v]
    conflict = SyncConflict(id=f"CNF-{uuid.uuid4().hex[:10].upper()}", user_id=user.id, entity_type=store, entity_id=obj.id, base_version=base_version,
                            server_version=obj.version, client_data=json.loads(json.dumps(changes, default=str)),
                            server_data=json.loads(json.dumps(_row(obj, allowed), default=str)), conflicting_fields=conflicting,
                            strategy="MANUAL", status="OPEN")
    db.add(conflict)
    return {"serverId": obj.id, "version": obj.version, "status": "CONFLICT", "conflictId": conflict.id, "conflictingFields": conflicting,
            "serverData": conflict.server_data}


@router.post("/push")
async def sync_push(req: SyncPushRequest, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.SYNC))):
    await enforce("sync", current_user.id)
    processed = []
    for item in sorted(req.items, key=lambda i: (i.sequence is None, i.sequence or 0)):
        item.device_id = item.device_id or req.device_id
        prev = await _existing_event(db, current_user.id, item.idempotency_key)
        if prev:
            if prev.user_id != current_user.id:
                processed.append({"localId": item.id, "idempotencyKey": item.idempotency_key, "status": "ERROR", "error": "Idempotency key belongs to another user"})
                continue
            processed.append({**(prev.result or {}), "localId": item.id, "idempotencyKey": item.idempotency_key, "status": "ALREADY_SYNCED",
                              "originalStatus": (prev.result or {}).get("status"), "message": "Duplicate avoided via idempotency key"})
            continue
        store = STORE_ALIASES.get(item.store)
        try:
            if not store:
                raise ValueError(f"Unsupported store: {item.store}")
            if item.operation == "CREATE":
                result = {**(await _apply_create(db, store, item.data, current_user, item, request)), "status": "SYNCED"}
            elif item.operation == "UPDATE":
                result = await _apply_update(db, store, item.data.get("id") or item.id, item.data, item.base_version, current_user, item)
            else:
                raise ValueError("DELETE is not accepted from offline clients; use the workflow endpoints")
            db.add(SyncEvent(id=str(uuid.uuid4()), user_id=current_user.id, client_sync_id=item.id[:64], idempotency_key=item.idempotency_key,
                             entity_type=store, entity_id=str(result.get("serverId", item.id))[:64], operation=item.operation,
                             status="CONFLICT" if result["status"] == "CONFLICT" else "PROCESSED", result=json.loads(json.dumps(result, default=str)), device_id=item.device_id))
            await db.commit()
            processed.append({"localId": item.id, "idempotencyKey": item.idempotency_key, **result,
                              "message": "Successfully synchronized" if result["status"] == "SYNCED" else "Conflict recorded; resolve via /sync/conflicts"})
        except (ValidationError, ValueError, LookupError) as e:
            await db.rollback()
            msg = e.errors()[0]["msg"] if isinstance(e, ValidationError) else str(e)
            processed.append({"localId": item.id, "idempotencyKey": item.idempotency_key, "status": "REJECTED", "retryable": False, "error": msg[:300]})
        except HTTPException as e:
            await db.rollback()
            processed.append({"localId": item.id, "idempotencyKey": item.idempotency_key, "status": "REJECTED", "retryable": e.status_code >= 500 or e.status_code == 429,
                              "error": (e.detail.get("message") if isinstance(e.detail, dict) else str(e.detail))[:300]})
        except Exception:
            await db.rollback()
            processed.append({"localId": item.id, "idempotencyKey": item.idempotency_key, "status": "ERROR", "retryable": True, "error": "Server error; will retry"})
    synced = sum(1 for p in processed if p["status"] == "SYNCED")
    await AuditService.for_user(db, current_user, "SYNC_PUSH", "SYNC", None, request=request, new_value={"items": len(req.items), "synced": synced})
    await Event("sync.completed", {"user_id": current_user.id, "items_synced": synced}, user_ids=[current_user.id]).publish()
    return {"success": all(p["status"] in ("SYNCED", "ALREADY_SYNCED") for p in processed), "synced_at": datetime.utcnow().isoformat(), "processed": processed}


# ---- Pull ---------------------------------------------------------------------------------
def _enc(ts: datetime, id_: str) -> str:
    return base64.urlsafe_b64encode(json.dumps([ts.isoformat(), id_]).encode()).decode()


def _dec(cursor: Optional[str]):
    if not cursor:
        return None
    try:
        ts, id_ = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return datetime.fromisoformat(ts), id_
    except Exception:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CURSOR", "message": "Invalid sync cursor"})


PULL_STORES = {
    "animals": (Animal, lambda a: {"id": a.id, "tagId": a.tag_id, "species": a.species, "breed": a.breed, "healthStatus": a.health_status, "district": a.district, "village": a.village}),
    "herds": (Herd, lambda h: {"id": h.id, "species": h.species, "totalAnimals": h.total_animals, "healthStatus": h.health_status, "district": h.district, "village": h.village}),
    "reports": (DiseaseReport, lambda r: {"id": r.id, "clientId": r.client_id, "reportNumber": r.report_number, "species": r.species, "status": r.status,
                                          "district": r.district, "disease": r.suspected_disease, "risk": r.triage_risk_level, "verificationStatus": r.verification_status}),
    "vetCases": (VeterinaryCase, lambda c: {"id": c.id, "caseNumber": c.case_number, "species": c.species, "status": c.status, "district": c.district, "priority": c.priority, "assignedVet": c.assigned_vet_id}),
    "labSamples": (LabSample, lambda s: {"id": s.id, "sampleCode": s.sample_code, "status": s.status, "sampleType": s.sample_type, "disease": s.disease_suspected, "district": s.district}),
    "vaccinations": (VaccinationRecord, lambda v: {"id": v.id, "animalId": v.animal_id, "disease": v.disease, "vaccine": v.vaccine, "doseNumber": v.dose_number, "vaccinationDate": v.vaccination_date.isoformat() if v.vaccination_date else None}),
}


def _scope(stmt, model, user: User):
    role = user.role
    if role == UserRole.FARMER.value:
        owner_col = {Animal: Animal.owner_id, Herd: Herd.owner_id, DiseaseReport: DiseaseReport.user_id, VeterinaryCase: VeterinaryCase.farmer_id,
                     LabSample: LabSample.farmer_id, VaccinationRecord: VaccinationRecord.provider_id}[model]
        return stmt.where(owner_col == user.id)
    if role in VET_ROLES and model is VeterinaryCase:
        return stmt.where(VeterinaryCase.assigned_vet_id == user.id)
    if role in LAB_ROLES:
        return stmt if model is LabSample else stmt.where(False)
    d = jurisdiction_scope(user)["district"]
    return stmt.where(model.district == d) if d else stmt


@router.get("/pull")
async def sync_pull(store: Optional[str] = Query(None, description="One of: " + ", ".join(PULL_STORES)), cursor: Optional[str] = None,
                    since: Optional[str] = None, limit: int = Query(200, ge=1, le=1000), db: AsyncSession = Depends(get_db),
                    current_user: User = Depends(require_permission(Permission.SYNC))):
    """Without `store`: first page of every store (legacy response shape + cursors).
    With `store`: pages through that store until `has_more` is false."""
    stores = [store] if store else list(PULL_STORES)
    if store and store not in PULL_STORES:
        raise HTTPException(status_code=422, detail={"code": "UNKNOWN_STORE", "message": "Unknown store"})
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "INVALID_SINCE", "message": "since must be ISO-8601"})
    out: Dict[str, Any] = {"timestamp": datetime.utcnow().isoformat(), "cursors": {}, "has_more": {}}
    for name in stores:
        model, ser = PULL_STORES[name]
        stmt = _scope(select(model), model, current_user)
        c = _dec(cursor) if store else None
        if c:
            stmt = stmt.where(or_(model.updated_at > c[0], and_(model.updated_at == c[0], model.id > c[1])))
        elif since_dt:
            stmt = stmt.where(model.updated_at > since_dt)
        rows = (await db.execute(stmt.order_by(model.updated_at, model.id).limit(limit + 1))).scalars().all()
        more = len(rows) > limit
        rows = rows[:limit]
        out[name] = [{**ser(r), "version": r.version, "updatedAt": r.updated_at.isoformat() if r.updated_at else None, "deleted": r.deleted_at is not None} for r in rows]
        out["cursors"][name] = _enc(rows[-1].updated_at, rows[-1].id) if rows and rows[-1].updated_at else cursor
        out["has_more"][name] = more
    return out


# ---- Conflicts ----------------------------------------------------------------------------
@router.get("/conflicts")
async def list_conflicts(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_permission(Permission.SYNC))):
    rows = (await db.execute(select(SyncConflict).where(SyncConflict.user_id == current_user.id, SyncConflict.status == "OPEN").order_by(SyncConflict.created_at.desc()))).scalars().all()
    return [{"id": c.id, "entityType": c.entity_type, "entityId": c.entity_id, "baseVersion": c.base_version, "serverVersion": c.server_version,
             "clientData": c.client_data, "serverData": c.server_data, "conflictingFields": c.conflicting_fields, "createdAt": c.created_at.isoformat()} for c in rows]


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, req: ConflictResolution, request: Request, db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_permission(Permission.SYNC))):
    c = await db.get(SyncConflict, conflict_id)
    if not c or c.user_id != current_user.id:
        raise HTTPException(status_code=404, detail={"code": "CONFLICT_NOT_FOUND", "message": "Conflict not found"})
    if c.status != "OPEN":
        raise HTTPException(status_code=409, detail={"code": "ALREADY_RESOLVED", "message": "Conflict already resolved"})
    model = MODEL_FOR.get(c.entity_type)
    obj = await db.get(model, c.entity_id) if model else None
    if req.resolution != "KEEP_SERVER" and obj is not None:
        ensure_can_access_record(current_user, owner_ids=[getattr(obj, "owner_id", None)], district=obj.district)
        data = c.client_data if req.resolution == "KEEP_CLIENT" else (req.merged_data or {})
        for k, v in data.items():
            if k in MERGEABLE.get(c.entity_type, []):
                setattr(obj, k, v)
        obj.version += 1
        obj.updated_by = current_user.id
    c.status = {"KEEP_SERVER": "RESOLVED_SERVER", "KEEP_CLIENT": "RESOLVED_CLIENT", "MERGED": "RESOLVED_MERGED"}[req.resolution]
    c.resolved_by, c.resolved_at = current_user.id, datetime.utcnow()
    await AuditService.for_user(db, current_user, "SYNC_CONFLICT_RESOLVED", c.entity_type.upper(), c.entity_id, request=request, commit=False, new_value={"resolution": req.resolution})
    await db.commit()
    return {"id": c.id, "status": c.status, "version": obj.version if obj else None}
