"""Callback queue API (PATH B — veterinarian was unavailable during the IVR call).

Veterinarians/officers can list the queue, accept a callback, mark it dialled, create a
case from the linked report, and mark it completed. Priority is the existing triage
severity (CRITICAL/HIGH/MODERATE/LOW). Every mutation is audited and broadcast over the
existing WebSocket event bus.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (CallbackRequest, DiseaseReport, User, UserRole,
                            VeterinaryCase)
from backend.security import (Permission, forbidden, jurisdiction_scope,
                              phone_for_viewer, require_permission)
from backend.services.audit_service import AuditService
from backend.services.events import Event
from backend.services.notification_service import NotificationService
from backend.services.workflow import record_transition

logger = logging.getLogger("pashu_shield.telephony")

router = APIRouter(prefix="/callbacks", tags=["IVR Callback Queue"])


def serialize_callback(cb: CallbackRequest, viewer: Optional[User] = None) -> dict:
    return {
        "id": cb.id,
        "callSessionId": cb.call_session_id,
        "reportId": cb.disease_report_id,
        "farmerId": cb.farmer_id,
        "callerPhone": phone_for_viewer(viewer, cb.caller_phone, owner_id=cb.farmer_id),
        "district": cb.district,
        "taluka": cb.taluka,
        "village": cb.village,
        "species": cb.species,
        "symptoms": list(cb.symptoms or []),
        "priority": cb.priority,          # existing triage severity
        "status": cb.status,
        "assignedVeterinarian": cb.assigned_veterinarian,
        "notes": cb.notes,
        "isSimulated": bool(cb.is_simulated),
        "demoLabel": "DEMO / SIMULATED" if cb.is_simulated else None,
        "acceptedAt": cb.accepted_at.isoformat() if cb.accepted_at else None,
        "completedAt": cb.completed_at.isoformat() if cb.completed_at else None,
        "createdAt": cb.created_at.isoformat() if cb.created_at else None,
        "callTime": cb.created_at.isoformat() if cb.created_at else None,
    }


def _scope_query(user: User, stmt):
    if user.role == UserRole.FARMER.value:
        return stmt.where(CallbackRequest.farmer_id == user.id)
    if user.role in (UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value):
        raise forbidden()
    if user.role in (UserRole.STATE_OFFICER.value, UserRole.SYSTEM_ADMIN.value):
        return stmt
    scope = jurisdiction_scope(user)
    if scope["district"]:
        # District-scoped: only callbacks in their district (or assigned to them).
        # Null-district callbacks stay with state/admin until located.
        stmt = stmt.where(or_(CallbackRequest.district == scope["district"],
                              CallbackRequest.assigned_veterinarian == user.id))
        if scope["taluka"]:
            stmt = stmt.where(or_(CallbackRequest.taluka == scope["taluka"],
                                  CallbackRequest.assigned_veterinarian == user.id))
    return stmt


@router.get("")
async def list_callbacks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CASE_READ)),
):
    stmt = select(CallbackRequest)
    stmt = _scope_query(current_user, stmt)
    if status:
        stmt = stmt.where(CallbackRequest.status == status.upper())
    if priority:
        stmt = stmt.where(CallbackRequest.priority == priority.upper())
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    order = {k: i for i, k in enumerate(["CRITICAL", "HIGH", "MODERATE", "LOW"])}
    rows = (await db.execute(stmt.order_by(CallbackRequest.created_at.desc()).offset(offset).limit(limit))).scalars().all()
    rows = sorted(rows, key=lambda c: (0 if c.status == "PENDING" else 1, order.get(c.priority, 9),
                                       -(c.created_at.timestamp() if c.created_at else 0)))
    return JSONResponse([serialize_callback(r, current_user) for r in rows],
                        headers={"X-Total-Count": str(total)})


async def _load(db: AsyncSession, cb_id: str) -> CallbackRequest:
    cb = await db.get(CallbackRequest, cb_id)
    if cb is None:
        raise HTTPException(status_code=404, detail={"code": "CALLBACK_NOT_FOUND", "message": "Callback not found"})
    return cb


@router.get("/{callback_id}")
async def callback_detail(callback_id: str, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_permission(Permission.CASE_READ))):
    cb = await _load(db, callback_id)
    scoped = (await db.execute(_scope_query(current_user, select(CallbackRequest).where(CallbackRequest.id == callback_id)))).scalars().all()
    if not scoped:
        raise forbidden("Callback is outside your scope", code="OUT_OF_JURISDICTION")
    report = await db.get(DiseaseReport, cb.disease_report_id) if cb.disease_report_id else None
    farmer = await db.get(User, cb.farmer_id) if cb.farmer_id else None
    return {
        **serialize_callback(cb, current_user),
        "farmerName": farmer.full_name if farmer else None,
        "reportNumber": report.report_number if report else None,
        "triageRiskLevel": report.triage_risk_level if report else None,
        "numberAffected": report.number_affected if report else None,
    }


@router.post("/{callback_id}/accept")
async def accept_callback(callback_id: str, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    cb = await _load(db, callback_id)
    if cb.status not in ("PENDING",):
        raise HTTPException(status_code=409, detail={"code": "NOT_PENDING", "message": "Callback is not pending"})
    old = cb.status
    cb.status, cb.assigned_veterinarian, cb.accepted_at = "ACCEPTED", current_user.id, datetime.utcnow()
    await AuditService.for_user(db, current_user, "CALLBACK_ACCEPTED", "CALLBACK", cb.id, request=request,
                                commit=False, old_value={"status": old}, new_value={"status": cb.status})
    await db.commit()
    await Event("call.callback_updated", {"callbackId": cb.id, "status": cb.status,
                                          "assigned": current_user.id},
                district=cb.district, taluka=cb.taluka, user_ids=[cb.farmer_id] if cb.farmer_id else []).publish()
    if cb.disease_report_id:
        report = await db.get(DiseaseReport, cb.disease_report_id)
        if report is not None and report.user_id:
            farmer = await db.get(User, report.user_id)
            if farmer is not None:
                await NotificationService.queue(db, channel="IN_APP", template="CASE_STATUS_UPDATED",
                                                context={"case_number": cb.id, "status": "CALLBACK_ACCEPTED"},
                                                user=farmer, dedup_key=f"cb-accepted:{cb.id}")
                await db.commit()
    return serialize_callback(cb, current_user)


@router.post("/{callback_id}/call-back")
async def mark_called_back(callback_id: str, request: Request, payload: Optional[dict] = None,
                           db: AsyncSession = Depends(get_db),
                           current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    """Veterinarian has dialled the farmer back — moves the callback to IN_PROGRESS."""
    cb = await _load(db, callback_id)
    if cb.status in ("COMPLETED", "CANCELLED"):
        raise HTTPException(status_code=409, detail={"code": "ALREADY_CLOSED", "message": "Callback is closed"})
    if cb.assigned_veterinarian is None:
        cb.assigned_veterinarian = current_user.id
        cb.accepted_at = cb.accepted_at or datetime.utcnow()
    note = ((payload or {}).get("notes") or "").strip()[:2000]
    if note:
        cb.notes = f"{cb.notes}\n---\n{note}" if cb.notes else note
    cb.status = "IN_PROGRESS"
    await AuditService.for_user(db, current_user, "CALLBACK_DIALLED", "CALLBACK", cb.id, request=request,
                                commit=False, new_value={"status": cb.status})
    await db.commit()
    await Event("call.callback_updated", {"callbackId": cb.id, "status": cb.status},
                district=cb.district, taluka=cb.taluka).publish()
    return serialize_callback(cb, current_user)


@router.post("/{callback_id}/complete")
async def complete_callback(callback_id: str, request: Request, payload: Optional[dict] = None,
                            db: AsyncSession = Depends(get_db),
                            current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    cb = await _load(db, callback_id)
    if cb.status == "COMPLETED":
        return {**serialize_callback(cb, current_user), "alreadyCompleted": True}
    note = ((payload or {}).get("notes") or "").strip()[:2000]
    if note:
        cb.notes = f"{cb.notes}\n---\n{note}" if cb.notes else note
    cb.status, cb.completed_at = "COMPLETED", datetime.utcnow()
    if cb.assigned_veterinarian is None:
        cb.assigned_veterinarian = current_user.id
    await AuditService.for_user(db, current_user, "CALLBACK_COMPLETED", "CALLBACK", cb.id, request=request,
                                commit=False, new_value={"status": "COMPLETED"})
    await db.commit()
    await Event("call.callback_updated", {"callbackId": cb.id, "status": cb.status},
                district=cb.district, taluka=cb.taluka).publish()
    return serialize_callback(cb, current_user)


@router.post("/{callback_id}/create-case")
async def create_case_from_callback(callback_id: str, request: Request, db: AsyncSession = Depends(get_db),
                                    current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    """Create (or return) the VeterinaryCase linked to the callback's disease report so a
    veterinarian can drive the existing case workflow. Never invents clinical data — all
    fields come from the existing report."""
    cb = await _load(db, callback_id)
    if cb.status in ("COMPLETED", "CANCELLED"):
        raise HTTPException(status_code=409, detail={"code": "ALREADY_CLOSED", "message": "Callback is closed"})
    if not cb.disease_report_id:
        raise HTTPException(status_code=409, detail={"code": "NO_REPORT", "message": "No disease report is linked to this callback"})
    report = await db.get(DiseaseReport, cb.disease_report_id)
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "REPORT_NOT_FOUND", "message": "Linked report not found"})
    existing = (await db.execute(select(VeterinaryCase).where(VeterinaryCase.report_id == report.id))).scalars().first()
    if existing is None:
        now = datetime.utcnow()
        case = VeterinaryCase(
            id=f"CASE-{uuid.uuid4().hex[:10].upper()}",
            case_number=f"CAS-{(report.district or 'UNK')[:3].upper()}-{now:%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            report_id=report.id,
            farmer_id=report.user_id if report.user_id else cb.farmer_id,
            status="REPORTED",
            priority=report.triage_risk_level or cb.priority,
            species=report.species, district=report.district, taluka=report.taluka, village=report.village,
            lat=report.lat, lng=report.lng, requires_lab=report.triage_risk_level in ("HIGH", "CRITICAL"),
            is_demo=report.is_demo,
            reported_problem=f"IVR callback {cb.id}: {', '.join(report.symptoms or []) or 'see report'}"[:900],
            risk_score={"CRITICAL": 85.0, "HIGH": 65.0, "MODERATE": 40.0}.get(report.triage_risk_level, 20.0),
        )
        db.add(case)
        await db.flush()
        record_transition(db, "CASE", case.id, None, "REPORTED", current_user, note=f"created from IVR callback {cb.id}")
        if cb.status == "PENDING":
            cb.status, cb.assigned_veterinarian, cb.accepted_at = "ACCEPTED", current_user.id, datetime.utcnow()
        await AuditService.for_user(db, current_user, "CALLBACK_CASE_CREATED", "CASE", case.id, request=request,
                                    commit=False, new_value={"callback": cb.id, "report": report.id})
        await db.commit()
        await Event("case.created", {"id": case.id, "caseNumber": case.case_number, "district": case.district,
                                     "status": case.status, "assignedVetId": case.assigned_vet_id},
                    district=case.district, taluka=case.taluka, user_ids=[current_user.id]).publish()
        existing = case
    return {"caseId": existing.id, "caseNumber": existing.case_number, "status": existing.status,
            "callback": serialize_callback(cb, current_user)}
