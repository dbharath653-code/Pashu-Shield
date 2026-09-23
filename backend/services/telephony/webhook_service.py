"""IVR webhook orchestration: signature-verified Twilio form parsing, idempotent CallSession
creation keyed on the provider CallSid, farmer identification by phone (signal only),
veterinarian availability search (existing DispatchEngine), survey flow, report creation
through the EXISTING report_service, callback queueing and call.* realtime events.

Every voice endpoint returns TwiML (never JSON) via services/telephony/twiml.py.
"""
from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import CallSession, CallbackRequest, DiseaseReport, IVRSurvey, User, UserRole
from backend.security import hash_password, mask_phone
from backend.services import call_events
from backend.services.audit_service import AuditService
from backend.services.dispatch_service import DispatchEngine
from backend.services.events import Event
from backend.services.ivr import prompts
from backend.services.ivr.survey_engine import SurveyEngine
from backend.services.report_service import submit_report
from backend.services.telephony import WebhookVerificationError, get_provider
from backend.services.telephony import call_router
from backend.services.telephony.twiml import (dial_for, gather_dtmf, public_base_url,
                                             redirect_to, say, twiml_response)

logger = logging.getLogger("pashu_shield.telephony")

IVR_SYSTEM_USER_ID = "IVR-SYSTEM-CALLER"


# ------------------------------------------------------------------------------------------
# Webhook parsing & verification
# ------------------------------------------------------------------------------------------
async def read_webhook(request: Request) -> Tuple[Dict[str, str], str]:
    """Parse the Twilio form POST and verify its signature (when enabled).
    Returns (params, call_sid_for_logging). Raises WebhookVerificationError on failure.

    Signature uses the BODY form fields only (Twilio's algorithm); routing parameters
    such as ?step= / ?q= are merged in afterwards so endpoint logic can see them.
    """
    form = await request.form()
    body_params = {str(k): str(v) if v is not None else "" for k, v in form.items()}
    # Signature is computed over the exact public URL the provider requested.
    if settings.PUBLIC_API_BASE_URL:
        expected_url = public_base_url(request) + request.url.path + (("?" + str(request.url.query)) if request.url.query else "")
    else:
        expected_url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature") or request.headers.get("X-Mock-Signature")
    # Canonical form body lets the mock provider verify a body-derived shared secret.
    canonical_body = urlencode(sorted(body_params.items())).encode()
    provider = get_provider()
    try:
        provider.validate_webhook(canonical_body, body_params, signature, expected_url)
    except WebhookVerificationError:
        logger.warning("webhook verification failed", extra={"fields": {
            "path": request.url.path, "call_sid": body_params.get("CallSid"),
            "remote": request.client.host if request.client else None}})
        raise
    params = {**dict(request.query_params), **body_params}
    call_sid = provider.get_call_sid(params) or "-"
    return params, call_sid


# ------------------------------------------------------------------------------------------
# CallSession idempotency
# ------------------------------------------------------------------------------------------
async def get_or_create_session(db: AsyncSession, params: Dict[str, str], call_sid: str) -> Tuple[CallSession, bool]:
    """Create the CallSession for a CallSid exactly once; duplicate webhooks / provider
    retries retrieve the existing row (unique index on provider_call_id)."""
    provider = get_provider()
    existing = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_sid))).scalars().first()
    if existing:
        return existing, False
    caller = provider.get_caller_number(params) or None
    if caller:
        caller = re.sub(r"[^\d+]", "", caller)[:32]
    session = CallSession(
        id=f"CAL-{uuid.uuid4().hex[:10].upper()}",
        provider=provider.name,
        provider_call_id=call_sid,
        caller_phone=caller,
        to_phone=(provider.get_called_number(params) or None),
        direction="INBOUND",
        status=call_router.INBOUND,
        recording_status="DISABLED" if not settings.CALL_RECORDING_ENABLED else "PENDING",
        transcription_status="NOT_CONFIGURED",
        vet_attempts=[],
        is_simulated=provider.is_mock,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    try:
        await db.flush()
        return session, True
    except IntegrityError:
        await db.rollback()
        existing = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_sid))).scalars().first()
        if existing is None:
            raise
        return existing, False


# ------------------------------------------------------------------------------------------
# Farmer identification (phone is a lookup signal, never proof of identity)
# ------------------------------------------------------------------------------------------
def _normalize_phone(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits or None


async def identify_farmer(db: AsyncSession, session: CallSession) -> Optional[User]:
    if session.farmer_id:
        return await db.get(User, session.farmer_id)
    digits = _normalize_phone(session.caller_phone)
    if not digits or len(digits) < 10:
        return None
    tail = digits[-10:]
    candidates = (await db.execute(select(User).where(
        User.role == UserRole.FARMER.value,
        User.is_active.is_(True),
        User.phone.isnot(None),
    ))).scalars().all()
    for u in candidates:
        ud = _normalize_phone(u.phone)
        if ud and ud[-10:] == tail:
            session.farmer_id = u.id
            session.district = session.district or u.district
            logger.info("farmer matched by phone (signal only)", extra={"fields": {
                "call_session": session.id, "farmer_id": u.id, "caller_masked": mask_phone(session.caller_phone)}})
            return u
    return None


async def get_or_create_ivr_system_user(db: AsyncSession) -> User:
    """Reporter of record for unregistered callers: a single, clearly-labelled system user
    (DiseaseReport.user_id must reference an existing user; the farmer's own profile is
    used whenever the phone number matches one)."""
    user = await db.get(User, IVR_SYSTEM_USER_ID)
    if user:
        return user
    user = User(
        id=IVR_SYSTEM_USER_ID,
        email="ivr.system@pashushield.local",
        phone=None,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        role=UserRole.FARMER.value,
        full_name="IVR Caller (unregistered)",
        state="Maharashtra",
        is_active=True,
        is_verified=True,
        is_demo=False,
        notification_language=settings.IVR_DEFAULT_LANGUAGE,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        user = await db.get(User, IVR_SYSTEM_USER_ID)
        if user is None:
            raise
    return user


# ------------------------------------------------------------------------------------------
# Veterinarian availability (PATH A) — reuses the existing dispatch eligibility engine
# ------------------------------------------------------------------------------------------
async def find_vet_candidates(db: AsyncSession, farmer: Optional[User], species: Optional[str] = None):
    if farmer is None or not farmer.district:
        return []  # unknown location => no provable jurisdiction match; go straight to survey
    return await DispatchEngine.find_eligible_veterinarians(db, farmer.district, lat=None, lng=None, species=species)


def attempted_vet_ids(session: CallSession) -> list:
    return [a.get("vet_id") for a in (session.vet_attempts or []) if a.get("vet_id")]


async def next_vet_candidate(db: AsyncSession, session: CallSession, farmer: Optional[User]) -> Optional[dict]:
    candidates = await find_vet_candidates(db, farmer)
    tried = set(attempted_vet_ids(session))
    if len(session.vet_attempts or []) >= settings.IVR_MAX_VET_ATTEMPTS:
        return None
    for c in candidates:
        if c["vet_id"] not in tried and c.get("phone"):
            return c
    return None


# ------------------------------------------------------------------------------------------
# Callback queue (PATH B)
# ------------------------------------------------------------------------------------------
async def create_callback_request(db: AsyncSession, session: CallSession,
                                  triage_risk: Optional[str], reporter: User,
                                  survey: Optional[IVRSurvey] = None) -> Optional[CallbackRequest]:
    """CallbackRequest uses the existing triage severity as its priority (no invented scores).
    When no report exists yet (cancelled/incomplete survey) any known answers are snapshotted
    from the survey — unknown fields simply stay null."""
    existing = (await db.execute(select(CallbackRequest).where(CallbackRequest.call_session_id == session.id))).scalars().first()
    if existing:
        return existing
    report = await db.get(DiseaseReport, session.disease_report_id) if session.disease_report_id else None
    priority = (triage_risk or (report.triage_risk_level if report else None) or "MODERATE").upper()
    if priority not in {"CRITICAL", "HIGH", "MODERATE", "LOW"}:
        priority = "MODERATE"
    species = report.species if report else None
    village = report.village if report else None
    district = report.district if report else None
    taluka = report.taluka if report else None
    symptoms = list(report.symptoms or []) if report else []
    if report is None and survey is not None:
        answers = await SurveyEngine.answers(db, survey)
        sp = answers.get("species")
        if isinstance(sp, str) and sp:
            species = sp
        loc = answers.get("location")
        farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
        if isinstance(loc, dict):
            if loc.get("registered") and farmer is not None:
                village, district, taluka = farmer.village, farmer.district, farmer.taluka
            elif isinstance(loc.get("village"), str):
                village = loc["village"]
                if farmer is not None and farmer.district:
                    district = farmer.district
        sym = answers.get("symptoms")
        if isinstance(sym, list):
            symptoms = list(sym)
    cb = CallbackRequest(
        id=f"CBK-{uuid.uuid4().hex[:10].upper()}",
        farmer_id=session.farmer_id or reporter.id,
        call_session_id=session.id,
        disease_report_id=session.disease_report_id,
        caller_phone=session.caller_phone,
        district=district,
        taluka=taluka,
        village=village,
        species=species,
        symptoms=symptoms,
        priority=priority,
        status="PENDING",
        is_simulated=session.is_simulated,
    )
    db.add(cb)
    await db.flush()
    return cb


# ------------------------------------------------------------------------------------------
# Realtime events (existing WebSocket infrastructure)
# ------------------------------------------------------------------------------------------
async def emit(session: CallSession, name: str, data: Optional[Dict[str, Any]] = None) -> None:
    await call_events.publish_call_event(name, session, data or {})


# ------------------------------------------------------------------------------------------
# TwiML flows
# ------------------------------------------------------------------------------------------
def _vr():
    from backend.services.telephony.twiml import VoiceResponse
    return VoiceResponse()


def disabled_twiml(request: Request):
    """IVR_ENABLED=false: polite message + hangup (safe way to turn the IVR off)."""
    vr = _vr()
    say(vr, prompts.prompt(settings.IVR_DEFAULT_LANGUAGE, "ivr_disabled"))
    vr.hangup()
    return twiml_response(vr)


def welcome_twiml(request: Request, language: Optional[str] = None):
    """Phase 1/2: welcome message + language selection gather (DTMF)."""
    vr = _vr()
    say(vr, prompts.WELCOME)
    gather = gather_dtmf(request, "/api/v1/telephony/ivr", prompts.LANGUAGE_MENU, language="en",
                         num_digits=1, timeout=8)
    vr.append(gather)
    # No input within timeout: repeat the menu once, then hang up politely.
    say(vr, prompts.LANGUAGE_MENU, language="en")
    vr.hangup()
    return twiml_response(vr)


def survey_twiml(request: Request, language: str, question_key: str, *, prefix: str = "", query: str = ""):
    """Gather for one survey question (DTMF primary; speech enabled on the location question)."""
    vr = _vr()
    if prefix:
        say(vr, prefix, language=language)
    prompt_text = SurveyEngine.question_prompt(language, question_key)
    speech = question_key == "location"
    multi = question_key in ("symptoms", "affected_count", "deaths")
    gather = gather_dtmf(
        request, "/api/v1/telephony/survey", prompt_text, language=language,
        query=query or f"q={question_key}",
        num_digits=0 if multi else 1,
        finish_on_key="#",
        timeout=8 if speech else 6,
        speech=speech,
    )
    vr.append(gather)
    # No input -> ask the same question again (keeps the flow alive without fabricating an answer).
    redirect_to(request, vr, "/api/v1/telephony/survey", query=query or f"q={question_key}")
    return twiml_response(vr)


def dial_vet_twiml(request: Request, session: CallSession, vet: dict):
    """PATH A: bridge the farmer with an available veterinarian using Twilio <Dial>."""
    vr = _vr()
    say(vr, prompts.prompt(session.language, "vet_search"), language=session.language)
    dial_for(request, vr, vet["phone"], action_path="/api/v1/telephony/ivr", query="step=vet_dial",
             timeout=settings.IVR_VET_TIMEOUT_SECONDS, recording=settings.CALL_RECORDING_ENABLED,
             status_callback_path="/api/v1/telephony/status")
    # If TwiML continues past <Dial> without an action result, fall through to the survey.
    redirect_to(request, vr, "/api/v1/telephony/ivr", query="step=survey")
    return twiml_response(vr)


async def begin_survey_twiml(request: Request, db: AsyncSession, session: CallSession, prefix_key: str = "vet_unavailable"):
    language = session.language or settings.IVR_DEFAULT_LANGUAGE
    survey = await SurveyEngine.start(db, session, language)
    call_router.apply_transition(session, call_router.SURVEY, reason="survey started")
    await db.commit()
    await emit(session, "call.survey_started", {"surveyId": survey.id, "language": language})
    first = survey.current_question if survey.current_question not in (None, "done") else "species"
    if survey.current_question in (None, "done"):
        survey.current_question = "species"
        await db.commit()
    return survey_twiml(request, language, first, prefix=prompts.prompt(language, prefix_key))


# ------------------------------------------------------------------------------------------
# Survey answer -> existing report pipeline
# ------------------------------------------------------------------------------------------
async def finalize_survey(db: AsyncSession, session: CallSession, survey: IVRSurvey):
    """On CONFIRM: create the EXISTING DiseaseReport via report_service.submit_report
    (rule triage -> VeterinaryCase -> dispatch offer -> alerts -> notifications -> audit),
    then queue a CallbackRequest (PATH B — no veterinarian answered this call).
    Returns the TwiML thank-you response."""
    language = session.language or settings.IVR_DEFAULT_LANGUAGE
    vr = _vr()

    reporter = await db.get(User, session.farmer_id) if session.farmer_id else None
    if reporter is None:
        reporter = await get_or_create_ivr_system_user(db)

    try:
        req = await SurveyEngine.build_report_create(db, session, survey)
    except ValueError as exc:
        # Required answers missing: never fabricate — abort honestly and queue a callback.
        survey.status = "ABANDONED"
        call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="survey incomplete")
        session.last_error = f"survey_incomplete:{exc}"
        cb = await create_callback_request(db, session, None, reporter, survey=survey)
        await db.commit()
        await emit(session, "call.callback_requested", {"callbackId": cb.id if cb else None, "reason": "survey_incomplete"})
        say(vr, prompts.prompt(language, "survey_aborted"), language=language)
        vr.hangup()
        return twiml_response(vr)

    call_router.apply_transition(session, call_router.CONFIRMATION, reason="survey confirmed")
    await db.commit()
    await emit(session, "call.survey_completed", {"surveyId": survey.id})

    # Existing pipeline: validate -> rule triage -> persist (SUBMITTED -> TRIAGED) ->
    # VeterinaryCase + dispatch offer -> deduplicated alert -> notifications -> audit.
    result = await submit_report(db, req, reporter, source="IVR")
    report_id = result["report"]["id"]
    risk = result["triage"]["risk_level"]

    session.disease_report_id = report_id
    if not session.district or session.district == "Unknown":
        session.district = req.district
    survey.disease_report_id = report_id
    survey.status = "COMPLETED"
    survey.completed_at = datetime.utcnow()
    call_router.apply_transition(session, call_router.REPORT_CREATED, reason=f"report {report_id}")
    call_router.apply_transition(session, call_router.TRIAGED, reason=f"triage {risk}")
    await db.commit()
    await emit(session, "call.report_created",
               {"reportId": report_id, "reportNumber": result["report"]["reportNumber"], "riskLevel": risk})
    await AuditService.log(db, "IVR_REPORT_CREATED", "REPORT", report_id,
                           user_id=reporter.id, user_name=reporter.full_name, role=reporter.role,
                           new_value={"call_session": session.id, "survey": survey.id, "triage": risk, "source": "IVR"})
    await Event("report.triaged", {"id": report_id, "riskLevel": risk, "source": "IVR"},
                district=req.district, taluka=req.taluka, owner_id=reporter.id).publish()
    await db.commit()

    # PATH B: nobody answered the farmer's call -> callback queue, priority = triage severity.
    cb = await create_callback_request(db, session, risk, reporter)
    call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="vet unavailable after survey")
    await db.commit()
    await emit(session, "call.callback_requested", {"callbackId": cb.id, "priority": cb.priority})

    say(vr, prompts.format_prompt(language, "report_created_callback",
                                  report_number=result["report"]["reportNumber"], risk=risk),
        language=language)
    vr.hangup()
    return twiml_response(vr)
