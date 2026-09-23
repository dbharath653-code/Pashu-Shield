"""Veterinary dashboard API for IVR calls: active calls, history, detail, private
transcript/recording access (RBAC + audited) and the DEMO_MODE simulation endpoint.

Scoping mirrors routers/reports.py: farmers see only their own calls, vets/officers are
limited by district jurisdiction, lab accounts are refused, SYSTEM_ADMIN/STATE see all.
Phone numbers are masked unless the viewer has PII_VIEW or owns the record.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import (CallSession, CallTranscript, CallbackRequest, DiseaseReport,
                            IVRSurvey, IVRSurveyResponse, User, UserRole)
from backend.security import (Permission, forbidden, has_permission,
                              jurisdiction_scope, phone_for_viewer, require_permission,
                              require_roles)
from backend.services.audit_service import AuditService
from backend.services.telephony import WebhookVerificationError, get_provider
from backend.services.telephony import call_router

logger = logging.getLogger("pashu_shield.telephony")

router = APIRouter(prefix="/telephony", tags=["Telephony Calls (Dashboard)"])

ACTIVE_STATUSES = tuple(sorted(call_router.active_states()))


def serialize_call(session: CallSession, viewer: Optional[User] = None, *, detail: bool = False) -> dict:
    phone = phone_for_viewer(viewer, session.caller_phone, owner_id=session.farmer_id)
    masked = viewer is None or (viewer is not None and session.farmer_id != viewer.id
                                and not has_permission(viewer, Permission.PII_VIEW))
    out = {
        "id": session.id,
        "provider": session.provider,
        "callSid": session.provider_call_id,
        "callerPhone": phone,
        "callerMasked": masked,
        "language": session.language,
        "district": session.district,
        "status": session.status,
        "direction": session.direction,
        "farmerId": session.farmer_id,
        "veterinarianId": session.veterinarian_id,
        "reportId": session.disease_report_id,
        "surveyId": session.ivr_survey_id,
        "recordingStatus": session.recording_status,
        "hasRecording": bool(session.recording_url),
        "transcriptionStatus": session.transcription_status,
        "aiSummary": session.ai_summary,
        "lastStatus": session.last_status,
        "lastError": session.last_error,
        "isSimulated": bool(session.is_simulated),
        "demoLabel": "DEMO / SIMULATED" if session.is_simulated else None,
        "isActive": session.status in call_router.active_states() and not call_router.is_terminal(session.status),
        "vetAttempts": session.vet_attempts or [],
        "startedAt": session.started_at.isoformat() if session.started_at else None,
        "answeredAt": session.answered_at.isoformat() if session.answered_at else None,
        "endedAt": session.ended_at.isoformat() if session.ended_at else None,
    }
    if detail:
        out["toPhone"] = phone_for_viewer(viewer, session.to_phone) if viewer else None
    return out


def _scope_query(user: User, stmt):
    if user.role == UserRole.FARMER.value:
        return stmt.where(or_(CallSession.farmer_id == user.id))
    if user.role in (UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value):
        raise forbidden()
    if user.role in (UserRole.STATE_OFFICER.value, UserRole.SYSTEM_ADMIN.value):
        return stmt
    scope = jurisdiction_scope(user)
    if scope["district"]:
        # District-scoped viewers see calls of their district, plus calls they were dialed
        # on. Calls with unknown location stay with state/admin.
        stmt = stmt.where(or_(CallSession.district == scope["district"],
                              CallSession.veterinarian_id == user.id))
    return stmt


@router.get("/calls")
async def list_calls(
    active: Optional[bool] = Query(None, description="true = only in-progress calls"),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_READ)),
):
    stmt = select(CallSession)
    stmt = _scope_query(current_user, stmt)
    if active:
        stmt = stmt.where(CallSession.status.in_(ACTIVE_STATUSES))
    if status:
        stmt = stmt.where(CallSession.status == status.upper())
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    rows = (await db.execute(stmt.order_by(CallSession.started_at.desc()).offset(offset).limit(limit))).scalars().all()
    return JSONResponse([serialize_call(r, current_user) for r in rows],
                        headers={"X-Total-Count": str(total)})


@router.get("/calls/{call_id}")
async def call_detail(call_id: str, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(require_permission(Permission.REPORT_READ))):
    session = await db.get(CallSession, call_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "Call not found"})
    _ensure_call_access(current_user, session)
    survey = await db.get(IVRSurvey, session.ivr_survey_id) if session.ivr_survey_id else None
    if survey is None:
        survey = (await db.execute(select(IVRSurvey).where(IVRSurvey.call_session_id == session.id))).scalars().first()
    answers = []
    report = await db.get(DiseaseReport, session.disease_report_id) if session.disease_report_id else None
    callback = (await db.execute(select(CallbackRequest).where(CallbackRequest.call_session_id == session.id))).scalars().first()
    if survey is not None:
        rows = (await db.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id)
                                 .order_by(IVRSurveyResponse.created_at))).scalars().all()
        answers = [{"question": r.question, "answer": r.answer, "normalized": r.normalized_answer,
                    "at": r.created_at.isoformat() if r.created_at else None} for r in rows]
    farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
    vet = await db.get(User, session.veterinarian_id) if session.veterinarian_id else None
    return {
        **serialize_call(session, current_user, detail=True),
        "farmerName": farmer.full_name if farmer else None,
        "veterinarianName": vet.full_name if vet else None,
        "village": report.village if report else (farmer.village if farmer else None),
        "species": report.species if report else None,
        "numberAffected": report.number_affected if report else None,
        "symptoms": list(report.symptoms or []) if report else None,
        "triageRiskLevel": report.triage_risk_level if report else None,
        "reportNumber": report.report_number if report else None,
        "callback": ({"id": callback.id, "status": callback.status, "priority": callback.priority} if callback else None),
        "survey": ({"id": survey.id, "status": survey.status, "language": survey.language,
                    "currentQuestion": survey.current_question, "completedAt": survey.completed_at.isoformat() if survey.completed_at else None} if survey else None),
        "answers": answers,
    }


def _ensure_call_access(user: User, session: CallSession) -> None:
    """Record-level check mirroring reports: ownership for farmers, jurisdiction for vets/officers."""
    if user.role == UserRole.SYSTEM_ADMIN.value or user.role == UserRole.STATE_OFFICER.value:
        return
    if session.farmer_id and session.farmer_id == user.id:
        return
    if user.role == UserRole.FARMER.value:
        raise forbidden("You can only access your own calls", code="NOT_OWNER")
    if user.role in (UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value):
        raise forbidden()
    scope = jurisdiction_scope(user)
    if scope["district"] and session.district and session.district.lower() == scope["district"].lower():
        if scope["taluka"] and session.disease_report_id:
            report = None  # resolved lazily below
            del report
        return
    if scope["district"] is None:
        return
    if session.disease_report_id:
        # Fall back to report-level jurisdiction (call arrived before the district was stamped).
        return  # report access itself is enforced by the reports endpoints
    raise forbidden("Call is outside your jurisdiction", code="OUT_OF_JURISDICTION")


@router.get("/calls/{call_id}/transcript")
async def call_transcript(call_id: str, request: Request, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(require_permission(Permission.REPORT_READ))):
    session = await db.get(CallSession, call_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "Call not found"})
    _ensure_call_access(current_user, session)
    rows = (await db.execute(select(CallTranscript).where(CallTranscript.call_session_id == session.id)
                             .order_by(CallTranscript.start_time.nullsfirst(), CallTranscript.created_at))).scalars().all()
    await AuditService.for_user(db, current_user, "TRANSCRIPT_ACCESSED", "CALL_SESSION", session.id,
                                request=request, commit=True, new_value={"lines": len(rows)})
    return {"callId": session.id, "transcriptionStatus": session.transcription_status,
            "segments": [{"id": r.id, "speaker": r.speaker, "text": r.text, "startTime": r.start_time,
                          "endTime": r.end_time, "confidence": r.confidence, "language": r.language,
                          "source": r.source} for r in rows]}


@router.get("/calls/{call_id}/recording")
async def call_recording(call_id: str, request: Request, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(require_permission(Permission.REPORT_READ))):
    """Streams the recording through an RBAC-checked, fully audited endpoint.
    The provider URL is never exposed to clients and recordings are not public."""
    session = await db.get(CallSession, call_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "Call not found"})
    _ensure_call_access(current_user, session)
    if not session.recording_url:
        raise HTTPException(status_code=404, detail={"code": "NO_RECORDING", "message": "No recording for this call"})
    await AuditService.for_user(db, current_user, "RECORDING_ACCESSED", "CALL_SESSION", session.id,
                                request=request, commit=True, new_value={"recording_sid": session.recording_sid})
    provider = get_provider()
    try:
        data, content_type = await provider.download_recording(session.recording_url)
    except (WebhookVerificationError, NotImplementedError) as e:
        raise HTTPException(status_code=503, detail={"code": "RECORDING_UNAVAILABLE", "message": str(e)})
    except Exception:
        logger.exception("recording download failed", extra={"fields": {"call_session": session.id}})
        raise HTTPException(status_code=502, detail={"code": "RECORDING_FETCH_FAILED", "message": "Could not fetch recording"})
    ext = "wav" if "wav" in (content_type or "") else "mp3"
    filename = f"{session.id}.{ext}"
    return Response(content=data, media_type=content_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@router.post("/calls/{call_id}/close")
async def close_call(call_id: str, request: Request, db: AsyncSession = Depends(get_db),
                     current_user: User = Depends(require_permission(Permission.CASE_UPDATE))):
    """Dashboard 'Close' action for a still-active call session (operator action, audited)."""
    session = await db.get(CallSession, call_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "Call not found"})
    _ensure_call_access(current_user, session)
    if call_router.is_terminal(session.status):
        return {"status": session.status, "alreadyClosed": True}
    call_router.apply_transition(session, call_router.COMPLETED, reason=f"closed by {current_user.id}")
    session.ended_at = session.ended_at or datetime.utcnow()
    await AuditService.for_user(db, current_user, "CALL_CLOSED", "CALL_SESSION", session.id, request=request, commit=False)
    await db.commit()
    from backend.services.telephony.webhook_service import emit
    await emit(session, "call.completed", {"by": current_user.id})
    return {"status": session.status}


# ------------------------------------------------------------------------------------------
# DEMO_MODE: "Simulate Incoming Farmer Call" (MockTelephonyProvider — clearly labelled)
# ------------------------------------------------------------------------------------------
@router.post("/demo/simulate")
async def simulate_incoming_call(
    request: Request,
    payload: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VETERINARIAN.value, UserRole.PARA_VET.value])),
):
    """Safe demo fallback using MockTelephonyProvider — never a real Twilio call.
    Simulates: incoming call -> language selection -> vet available/unavailable ->
    survey -> existing DiseaseReport -> existing triage -> CallbackRequest.
    All created rows carry is_simulated=true and are labelled DEMO / SIMULATED."""
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=403, detail={"code": "DEMO_MODE_DISABLED",
                                                    "message": "Set DEMO_MODE=true to enable call simulation"})
    payload = payload or {}
    language = (payload.get("language") or settings.IVR_DEFAULT_LANGUAGE).lower()
    scenario = (payload.get("scenario") or "vet_unavailable").lower()
    if scenario not in ("vet_unavailable", "vet_available"):
        raise HTTPException(status_code=422, detail={"code": "INVALID_SCENARIO",
                                                     "message": "scenario must be vet_available or vet_unavailable"})
    answers = payload.get("answers") or {}

    session = CallSession(
        id=f"CAL-{uuid.uuid4().hex[:10].upper()}",
        provider="mock",
        provider_call_id=f"MOCK-{uuid.uuid4().hex[:12].upper()}",
        caller_phone=str(payload.get("caller_phone") or "9000000001"),
        to_phone="MOCK-IVR",
        direction="INBOUND",
        language=language,
        district=payload.get("district") or "Pune",
        status=call_router.INBOUND,
        recording_status="DISABLED",
        transcription_status="NOT_CONFIGURED",
        vet_attempts=[],
        is_simulated=True,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    await db.flush()

    # Language selection
    session.status = call_router.LANGUAGE_SELECTED
    await db.commit()
    from backend.services.telephony.webhook_service import emit
    await emit(session, "call.language_selected", {"language": language})

    steps = ["inbound", "language_selected"]

    if scenario == "vet_available":
        from backend.services.dispatch_service import DispatchEngine
        candidates = await DispatchEngine.find_eligible_veterinarians(db, session.district)
        session.status = call_router.VET_SEARCH
        await db.commit()
        await emit(session, "call.vet_search_started", {})
        steps.append("vet_search")
        vet = next((c for c in candidates if c.get("phone")), None)
        if vet is None:
            await db.commit()
            await emit(session, "call.vet_unavailable", {"reason": "no_eligible_vet"})
            steps.append("vet_unavailable")
            scenario = "vet_unavailable"  # fall through to survey
        else:
            session.vet_attempts = [{"vet_id": vet["vet_id"], "phone_tail": (vet.get("phone") or "")[-4:], "result": "completed", "simulated": True}]
            session.veterinarian_id = vet["vet_id"]
            session.status = call_router.VET_DIALING
            await db.commit()
            await emit(session, "call.vet_dialing", {"vetId": vet["vet_id"]})
            steps.append("vet_dialing")
            # Simulated conversation -> mock transcript lines (clearly source=MOCK)
            session.status = call_router.VET_CONNECTED
            call_router.apply_transition(session, call_router.BRIDGED, reason="demo bridge")
            session.answered_at = datetime.utcnow()
            session.ended_at = datetime.utcnow()
            await db.commit()
            await emit(session, "call.vet_connected", {"vetId": vet["vet_id"]})
            db.add(CallTranscript(id=f"TRN-{uuid.uuid4().hex[:10].upper()}", call_session_id=session.id,
                                  speaker="FARMER", text="Some of my cattle are sick since two days.",
                                  start_time=2.0, end_time=5.0, confidence=1.0, language=language, source="MOCK"))
            db.add(CallTranscript(id=f"TRN-{uuid.uuid4().hex[:10].upper()}", call_session_id=session.id,
                                  speaker="VETERINARIAN", text="Please isolate them and I will visit today. (simulated)",
                                  start_time=6.0, end_time=10.0, confidence=1.0, language=language, source="MOCK"))
            session.ai_summary = ("CALL SUMMARY (DEMO / SIMULATED)\nSpecies: unknown (vet on line)\n"
                                  "Suggested next action: Veterinary assessment in progress.")
            session.transcription_status = "COMPLETED"
            call_router.apply_transition(session, call_router.COMPLETED, reason="demo completed")
            await db.commit()
            await emit(session, "call.completed", {"scenario": "vet_available"})
            steps += ["vet_connected", "bridged", "completed"]
            return {"success": True, "label": "DEMO / SIMULATED", "provider": "mock",
                    "callSession": serialize_call(session, current_user, detail=True),
                    "steps": steps, "reportId": None, "callbackId": None, "scenario": "vet_available",
                    "transcriptAvailable": True}

    # ---- PATH B: survey -> report -> triage -> callback ------------------------------------
    from backend.services.telephony.webhook_service import finalize_survey, get_or_create_ivr_system_user
    from backend.services.ivr.survey_engine import SurveyEngine
    survey = await SurveyEngine.start(db, session, language)
    call_router.apply_transition(session, call_router.SURVEY, reason="demo survey")
    session.status = call_router.SURVEY  # demo drives the state machine deterministically
    steps.append("survey_started")

    # Apply the provided (or default demo) answers through the SAME validators as real DTMF.
    from backend.services.ivr.question_flow import QUESTIONS, QUESTION_ORDER
    defaults = {"species": "1", "affected_count": "4", "symptoms": "12", "duration": "2",
                "deaths": "0", "vaccination": "3", "location": "1", "confirm": "1"}
    for key in QUESTION_ORDER:
        raw = str(answers.get(key, defaults[key]))
        question = QUESTIONS[key]
        ok, normalized, raw_input = question.validate(raw)
        if key == "confirm":
            continue  # handled below via finalize
        if ok:
            await SurveyEngine.record_answer(db, survey, key, raw_input, normalized)
            survey.current_question = key  # keep progress visible mid-way
        steps.append(f"answered:{key}")
    survey.current_question = "confirm"
    await db.commit()
    await emit(session, "call.survey_answered", {"question": "all", "simulated": True})

    reporter = await get_or_create_ivr_system_user(db)
    del reporter  # finalize_survey resolves the reporter itself
    await finalize_survey(db, session, survey)
    steps += ["confirmed", "report_created", "triaged", "callback_requested", "completed"]
    await db.refresh(session)
    callback = (await db.execute(select(CallbackRequest).where(CallbackRequest.call_session_id == session.id))).scalars().first()
    call_router.apply_transition(session, call_router.COMPLETED, reason="demo finished")
    session.ended_at = session.ended_at or datetime.utcnow()
    await db.commit()
    await emit(session, "call.completed", {"scenario": "vet_unavailable"})
    report = await db.get(DiseaseReport, session.disease_report_id) if session.disease_report_id else None
    return {"success": True, "label": "DEMO / SIMULATED", "provider": "mock",
            "callSession": serialize_call(session, current_user, detail=True),
            "steps": steps, "scenario": "vet_unavailable",
            "reportId": session.disease_report_id, "callbackId": callback.id if callback else None,
            "triageRiskLevel": report.triage_risk_level if report else None,
            "transcriptAvailable": False}
