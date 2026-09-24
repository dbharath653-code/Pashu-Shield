"""IVR webhook orchestration for the Exotel transport.

Responsibilities, in order:

  1. **Trust** the inbound request (``read_webhook``): Exotel does not sign webhooks, so the
     shared ``EXOTEL_WEBHOOK_SECRET`` carried in the ExoML action URL is the trust anchor,
     optionally backed by an authenticated CallSid lookup. Fails closed.
  2. **Normalise** provider fields through the active ``TelephonyProvider`` — nothing here
     reads an Exotel parameter name directly.
  3. **Idempotency**: one ``CallSession`` per provider call id (unique index), so Exotel
     retries can never create a second session, a second report, or a second case.
  4. **Identify** the caller by phone as a *lookup signal only* — never as proof of identity.
     An unknown caller is recorded as unknown; no location is ever invented.
  5. **Drive the flow** (language -> main menu -> report survey / veterinarian bridge /
     case status / emergency) using provider-neutral ``VoiceDoc`` instructions.
  6. **Hand off to existing services**: ``report_service.submit_report`` (rule triage ->
     ``DiseaseReport`` -> ``VeterinaryCase`` -> dispatch offer -> alerts -> notifications ->
     audit), ``DispatchEngine`` for veterinarian availability, ``NotificationService``, and
     the existing WebSocket event bus via ``call_events``.

The IVR owns no business logic of its own: it collects and validates input, then calls the
same pipeline the web and offline clients use.
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
from backend.models import (CallbackRequest, CallSession, DiseaseReport, IVRSurvey,
                            User, UserRole, VeterinaryCase)
from backend.security import hash_password, mask_phone
from backend.services import call_events
from backend.services.audit_service import AuditService
from backend.services.dispatch_service import DispatchEngine
from backend.services.events import Event
from backend.services.ivr import prompts
from backend.services.ivr.menu import MENU_REPORT, MENU_VETERINARIAN, MENU_CASE_STATUS, MENU_EMERGENCY, parse_menu_option
from backend.services.ivr.survey_engine import SurveyEngine
from backend.services.report_service import submit_report
from backend.services.telephony import WebhookVerificationError, get_provider
from backend.services.telephony import call_router
from backend.services.telephony.exoml import action_url
from backend.services.telephony.markup import VoiceDoc

logger = logging.getLogger("pashu_shield.telephony")

IVR_SYSTEM_USER_ID = "IVR-SYSTEM-CALLER"
#: Query parameter carrying the shared webhook secret inside ExoML action URLs.
WEBHOOK_TOKEN_PARAM = "t"
MAX_PARAM_LEN = 2000


# ------------------------------------------------------------------------------------------
# Observability (structured, secret-free)
# ------------------------------------------------------------------------------------------
def log_ivr(event: str, **fields: Any) -> None:
    """Emit one structured IVR log line. Never carries a phone number in full, a transcript,
    or any credential."""
    payload = {"event": event, "timestamp": datetime.utcnow().isoformat() + "Z"}
    payload.update({k: v for k, v in fields.items() if v is not None})
    logger.info("ivr", extra={"fields": payload})


def warn_ivr(event: str, **fields: Any) -> None:
    payload = {"event": event, "timestamp": datetime.utcnow().isoformat() + "Z"}
    payload.update({k: v for k, v in fields.items() if v is not None})
    logger.warning("ivr", extra={"fields": payload})


# ------------------------------------------------------------------------------------------
# Webhook trust + parsing
# ------------------------------------------------------------------------------------------
def webhook_token_query() -> str:
    """``t=<secret>`` query fragment appended to every ExoML action URL, or "" when no
    secret is configured (local development with EXOTEL_VALIDATE_WEBHOOK=false)."""
    if not settings.EXOTEL_WEBHOOK_SECRET:
        return ""
    return f"{WEBHOOK_TOKEN_PARAM}={settings.EXOTEL_WEBHOOK_SECRET}"


def _clip(value: str) -> str:
    """Bound a provider-supplied string before it is stored or logged."""
    return (value or "")[:MAX_PARAM_LEN]


async def read_webhook(request: Request) -> Tuple[Dict[str, str], str]:
    """Parse an Exotel webhook and verify it can be trusted.

    Exotel POSTs ``application/x-www-form-urlencoded`` by default; ``StatusCallbackContentType``
    can also be ``application/json``, so both are accepted. Routing hints (``step``, ``q``)
    live in the query string and are merged in afterwards.

    Returns ``(params, call_id)``; raises ``WebhookVerificationError`` when untrusted.
    """
    provider = get_provider()
    body_params = await _read_body_params(request)
    query_params = {str(k): str(v) for k, v in request.query_params.items()}

    secret = (request.headers.get(provider.secret_header)
              or request.headers.get("X-Webhook-Secret")
              or query_params.get(WEBHOOK_TOKEN_PARAM))
    canonical_body = urlencode(sorted(body_params.items())).encode()
    try:
        provider.validate_webhook(canonical_body, body_params, secret)
    except WebhookVerificationError as exc:
        warn_ivr("IVR_WEBHOOK_REJECTED", reason=str(exc), path=request.url.path,
                 remote=request.client.host if request.client else None)
        raise

    params = {**query_params, **{k: _clip(v) for k, v in body_params.items()}}
    call_id = provider.get_call_id(params) or "-"

    # Optional second factor: confirm an unknown call id belongs to our Exotel account.
    if settings.EXOTEL_VERIFY_CALL_SID and call_id != "-":
        if not await provider.verify_call_id(call_id):
            warn_ivr("IVR_WEBHOOK_REJECTED", reason="call_id_not_verified", call_id=call_id,
                     path=request.url.path)
            raise WebhookVerificationError("call id could not be verified with the provider")
    return params, call_id


async def _read_body_params(request: Request) -> Dict[str, str]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = await request.json()
        except ValueError:
            raise WebhookVerificationError("malformed JSON body")
        if not isinstance(payload, dict):
            raise WebhookVerificationError("JSON body must be an object")
        return {str(k): _flatten(v) for k, v in payload.items()}
    try:
        form = await request.form()
    except Exception as exc:  # malformed multipart / urlencoded body
        raise WebhookVerificationError(f"malformed form body: {type(exc).__name__}")
    return {str(k): ("" if v is None else str(v)) for k, v in form.items()}


def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    import json

    return json.dumps(value, separators=(",", ":"), default=str)[:MAX_PARAM_LEN]


# ------------------------------------------------------------------------------------------
# CallSession idempotency
# ------------------------------------------------------------------------------------------
async def get_or_create_session(db: AsyncSession, params: Dict[str, str], call_id: str) -> Tuple[CallSession, bool]:
    """Create the CallSession for a provider call id exactly once. Duplicate webhooks and
    provider retries retrieve the existing row (unique index on ``provider_call_id``)."""
    provider = get_provider()
    existing = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_id))).scalars().first()
    if existing:
        return existing, False
    caller = provider.get_caller_number(params)
    if caller:
        caller = re.sub(r"[^\d+]", "", caller)[:32] or None
    session = CallSession(
        id=f"CAL-{uuid.uuid4().hex[:10].upper()}",
        provider=provider.name,
        provider_call_id=call_id,
        caller_phone=caller,
        to_phone=provider.get_called_number(params),
        direction="INBOUND",
        status=call_router.INBOUND,
        recording_status="DISABLED" if not settings.CALL_RECORDING_ENABLED else "PENDING",
        transcription_status="NOT_CONFIGURED",
        vet_attempts=[],
        is_simulated=provider.is_mock,
        is_emergency=False,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    try:
        await db.flush()
        return session, True
    except IntegrityError:
        # Concurrent duplicate webhook: the other request won the insert.
        await db.rollback()
        existing = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_id))).scalars().first()
        if existing is None:
            raise
        return existing, False


# ------------------------------------------------------------------------------------------
# Caller identification (a phone match is a lookup signal, never proof of identity)
# ------------------------------------------------------------------------------------------
def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Digits-only form of a phone number (safe to compare, never logged in full)."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return digits or None


async def identify_farmer(db: AsyncSession, session: CallSession) -> Optional[User]:
    """Match the caller's number against active farmer profiles (last 10 digits).

    Returns ``None`` for an unknown caller. The session then carries *no* district — the
    IVR asks the caller for a location instead of assuming one.
    """
    if session.farmer_id:
        return await db.get(User, session.farmer_id)
    digits = normalize_phone(session.caller_phone)
    if not digits or len(digits) < 10:
        return None
    tail = digits[-10:]
    candidates = (await db.execute(select(User).where(
        User.role == UserRole.FARMER.value,
        User.is_active.is_(True),
        User.phone.isnot(None),
    ))).scalars().all()
    for user in candidates:
        user_digits = normalize_phone(user.phone)
        if user_digits and user_digits[-10:] == tail:
            session.farmer_id = user.id
            session.district = session.district or user.district
            log_ivr("IVR_CALLER_IDENTIFIED", call_id=session.provider_call_id,
                    call_session=session.id, farmer_id=user.id,
                    caller_masked=mask_phone(session.caller_phone))
            return user
    return None


async def get_or_create_ivr_system_user(db: AsyncSession) -> User:
    """Reporter of record for an unregistered caller: one clearly-labelled system user.

    ``DiseaseReport.user_id`` must reference an existing user; the caller's own profile is
    always used when the number matches one. The system user has no phone and no village, so
    nothing about an unknown caller's identity or location is fabricated.
    """
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
# Veterinarian availability (PATH A) — the existing dispatch eligibility engine
# ------------------------------------------------------------------------------------------
async def find_vet_candidates(db: AsyncSession, farmer: Optional[User], species: Optional[str] = None):
    if farmer is None or not farmer.district:
        return []  # unknown location => no provable jurisdiction match; go to the survey
    return await DispatchEngine.find_eligible_veterinarians(db, farmer.district, lat=None, lng=None, species=species)


def attempted_vet_ids(session: CallSession) -> list:
    return [a.get("vet_id") for a in (session.vet_attempts or []) if a.get("vet_id")]


async def next_vet_candidate(db: AsyncSession, session: CallSession, farmer: Optional[User]) -> Optional[dict]:
    if len(session.vet_attempts or []) >= settings.IVR_MAX_VET_ATTEMPTS:
        return None
    tried = set(attempted_vet_ids(session))
    for candidate in await find_vet_candidates(db, farmer):
        if candidate["vet_id"] not in tried and candidate.get("phone"):
            return candidate
    return None


# ------------------------------------------------------------------------------------------
# Callback queue (PATH B)
# ------------------------------------------------------------------------------------------
async def create_callback_request(db: AsyncSession, session: CallSession,
                                  triage_risk: Optional[str], reporter: User,
                                  survey: Optional[IVRSurvey] = None,
                                  reason: str = "") -> Optional[CallbackRequest]:
    """Queue a callback for this call. Priority reuses the existing triage severity —
    no score is invented here. Unknown fields stay null."""
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
        found_species = answers.get("species")
        if isinstance(found_species, str) and found_species:
            species = found_species
        location = answers.get("location")
        farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
        if isinstance(location, dict):
            if location.get("registered") and farmer is not None:
                village, district, taluka = farmer.village, farmer.district, farmer.taluka
            elif isinstance(location.get("village"), str):
                village = location["village"]
                if farmer is not None and farmer.district:
                    district = farmer.district
        reported = answers.get("symptoms")
        if isinstance(reported, list):
            symptoms = list(reported)
    notes = f"IVR call {session.id}" + (f" ({reason})" if reason else "")
    if session.is_emergency:
        notes += "; caller reported an EMERGENCY (menu 0) — priority above is the triage result"
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
        notes=notes[:2000],
    )
    db.add(cb)
    await db.flush()
    return cb


# ------------------------------------------------------------------------------------------
# Realtime events (existing WebSocket infrastructure)
# ------------------------------------------------------------------------------------------
async def emit(session: CallSession, name: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Publish a realtime dashboard event. A WebSocket/Redis outage must never break the
    call the farmer is on: the failure is logged and the call continues."""
    try:
        await call_events.publish_call_event(name, session, data or {})
    except Exception as exc:
        warn_ivr("IVR_EVENT_PUBLISH_FAILED", call_session=session.id, event=name,
                 error=type(exc).__name__)


# ------------------------------------------------------------------------------------------
# Voice flows (provider-neutral; rendered as ExoML by the active provider)
# ------------------------------------------------------------------------------------------
def disabled_doc() -> VoiceDoc:
    """IVR_ENABLED=false: polite message + hangup (the safe way to turn the IVR off)."""
    return VoiceDoc().say_and_hangup(prompts.prompt(settings.IVR_DEFAULT_LANGUAGE, "ivr_disabled"))


def goodbye_doc(language: Optional[str]) -> VoiceDoc:
    return VoiceDoc().say_and_hangup(prompts.prompt(language, "call_bye"), language=language)


def welcome_doc(request: Request) -> VoiceDoc:
    """Welcome + language selection. No input within the gather timeout repeats the menu
    once and then hangs up politely."""
    action = action_url(request, "/api/v1/ivr/input", "step=language")
    return (VoiceDoc()
            .say(prompts.WELCOME)
            .gather(prompts.LANGUAGE_MENU, action, language="en", num_digits=1, timeout=8)
            .say(prompts.LANGUAGE_MENU, language="en")
            .hangup())


def menu_doc(request: Request, language: Optional[str]) -> VoiceDoc:
    """Main menu: 1 report sick animal, 2 request a veterinarian, 3 case status, 0 emergency."""
    action = action_url(request, "/api/v1/ivr/input", "step=menu")
    text = prompts.prompt(language, "main_menu")
    return (VoiceDoc()
            .gather(text, action, language=language, num_digits=1, timeout=8)
            .say(text, language=language)
            .hangup())


def survey_doc(request: Request, language: str, question_key: str, *, prefix: str = "", query: str = "") -> VoiceDoc:
    """One survey question. DTMF is always the supported input; speech is requested only when
    the provider actually offers it, so a caller is never told to speak into a DTMF-only line."""
    provider = get_provider()
    if prefix:
        doc = VoiceDoc().say(prefix, language=language)
    else:
        doc = VoiceDoc()
    prompt_text = SurveyEngine.question_prompt(language, question_key)
    multi = question_key in ("symptoms", "affected_count", "deaths")
    wants_speech = question_key == "location"
    if wants_speech and not provider.supports_speech_input:
        prompt_text = prompts.prompt(language, "location_dtmf")
    doc.gather(
        prompt_text,
        action_url(request, "/api/v1/ivr/input", query or f"step=survey&q={question_key}"),
        language=language,
        num_digits=0 if multi else 1,
        finish_on_key="#",
        timeout=8 if wants_speech else 6,
        speech=wants_speech,
    )
    # No input -> ask the same question again (never fabricate an answer).
    return doc.redirect(action_url(request, "/api/v1/ivr/input", query or f"step=survey&q={question_key}"))


def dial_vet_doc(request: Request, session: CallSession, vet: dict) -> VoiceDoc:
    """PATH A: bridge the farmer with an available veterinarian.

    ExoML ``<Dial>`` reports the bridged-leg outcome on its ``action`` URL as
    ``DialCallStatus`` (there is no separate status-callback attribute), and control returns
    to the ``<Redirect>`` below when the leg ends without a result.
    """
    doc = VoiceDoc().say(prompts.prompt(session.language, "vet_search"), language=session.language)
    doc.dial(
        vet["phone"],
        action_url(request, "/api/v1/ivr/input", "step=vet_dial"),
        timeout=settings.IVR_VET_TIMEOUT_SECONDS,
        record=settings.CALL_RECORDING_ENABLED,
    )
    return doc.redirect(action_url(request, "/api/v1/ivr/input", "step=survey"))


def case_status_doc(request: Request, session: CallSession, case: Optional[VeterinaryCase],
                    report: Optional[DiseaseReport]) -> VoiceDoc:
    """Option 3. Only reached for a caller whose number matched their own registered profile,
    so no other farmer's case can be disclosed."""
    doc = VoiceDoc()
    if case is None and report is None:
        return doc.say_and_hangup(prompts.prompt(session.language, "case_status_none"),
                                  language=session.language)
    doc.say(prompts.format_prompt(
        session.language, "case_status",
        case_number=(case.case_number if case else (report.report_number if report else "")),
        status=(case.status if case else (report.status if report else "UNKNOWN")),
        risk=(report.triage_risk_level if report else "UNKNOWN"),
    ), language=session.language)
    return doc.hangup()


async def begin_survey(request: Request, db: AsyncSession, session: CallSession,
                       prefix_key: str = "vet_unavailable") -> VoiceDoc:
    language = session.language or settings.IVR_DEFAULT_LANGUAGE
    survey = await SurveyEngine.start(db, session, language)
    call_router.apply_transition(session, call_router.SURVEY, reason="survey started")
    await db.commit()
    await emit(session, "call.survey_started", {"surveyId": survey.id, "language": language})
    if survey.current_question in (None, "done"):
        survey.current_question = "species"
        await db.commit()
    log_ivr("IVR_SURVEY_STARTED", call_id=session.provider_call_id, call_session=session.id,
            survey_id=survey.id, language=language)
    prefix = prompts.prompt(language, "emergency_intro" if session.is_emergency else prefix_key)
    return survey_doc(request, language, survey.current_question, prefix=prefix)


# ------------------------------------------------------------------------------------------
# Survey answer -> existing report pipeline
# ------------------------------------------------------------------------------------------
async def finalize_survey(db: AsyncSession, session: CallSession, survey: IVRSurvey) -> VoiceDoc:
    """On CONFIRM: create the report through ``report_service.submit_report`` — the same
    pipeline the web app uses (rule triage -> ``DiseaseReport`` -> ``VeterinaryCase`` ->
    dispatch offer -> deduplicated alert -> notifications -> audit). Then queue a callback
    (PATH B: no veterinarian answered this call)."""
    language = session.language or settings.IVR_DEFAULT_LANGUAGE

    reporter = await db.get(User, session.farmer_id) if session.farmer_id else None
    if reporter is None:
        reporter = await get_or_create_ivr_system_user(db)

    try:
        req = await SurveyEngine.build_report_create(db, session, survey)
    except ValueError as exc:
        # A required answer is missing: never fabricate — abort honestly, queue a callback.
        survey.status = "ABANDONED"
        call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="survey incomplete")
        session.last_error = f"survey_incomplete:{exc}"
        cb = await create_callback_request(db, session, None, reporter, survey=survey, reason="survey_incomplete")
        await db.commit()
        await emit(session, "call.callback_requested",
                   {"callbackId": cb.id if cb else None, "reason": "survey_incomplete"})
        warn_ivr("IVR_CALL_FAILED", call_id=session.provider_call_id, call_session=session.id,
                 reason="survey_incomplete", detail=str(exc))
        return VoiceDoc().say_and_hangup(prompts.prompt(language, "survey_aborted"), language=language)

    call_router.apply_transition(session, call_router.CONFIRMATION, reason="survey confirmed")
    await db.commit()
    await emit(session, "call.survey_completed", {"surveyId": survey.id})

    result = await submit_report(db, req, reporter, source="IVR")
    report_id = result["report"]["id"]
    assigned = result.get("assignedCase") or {}
    case_id = assigned.get("caseId")
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
               {"reportId": report_id, "reportNumber": result["report"]["reportNumber"],
                "riskLevel": risk, "caseId": case_id, "emergency": bool(session.is_emergency)})
    log_ivr("IVR_CASE_CREATED", call_id=session.provider_call_id, call_session=session.id,
            report_id=report_id, case_id=case_id, triage_risk=risk,
            emergency=bool(session.is_emergency), source="IVR")
    await AuditService.log(db, "IVR_REPORT_CREATED", "REPORT", report_id,
                           user_id=reporter.id, user_name=reporter.full_name, role=reporter.role,
                           new_value={"call_session": session.id, "survey": survey.id, "triage": risk,
                                      "source": "IVR", "case_id": case_id,
                                      "emergency": bool(session.is_emergency)})
    await Event("report.triaged", {"id": report_id, "riskLevel": risk, "source": "IVR"},
                district=req.district, taluka=req.taluka, owner_id=reporter.id).publish()
    await db.commit()

    cb = await create_callback_request(db, session, risk, reporter,
                                       reason="emergency" if session.is_emergency else "vet_unavailable")
    call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="no veterinarian on this call")
    await db.commit()
    await emit(session, "call.callback_requested", {"callbackId": cb.id, "priority": cb.priority})

    return VoiceDoc().say_and_hangup(
        prompts.format_prompt(language, "report_created_callback",
                              report_number=result["report"]["reportNumber"], risk=risk),
        language=language)


# ------------------------------------------------------------------------------------------
# Case status lookup (option 3)
# ------------------------------------------------------------------------------------------
async def recent_case_for(db: AsyncSession, session: CallSession) -> Tuple[Optional[VeterinaryCase], Optional[DiseaseReport]]:
    """Most recent veterinary case (and its report) owned by the *identified* caller.

    Returns ``(None, None)`` for an unverified caller: another farmer's case must never be
    readable over the phone, and an unknown number proves nothing.
    """
    if not session.farmer_id:
        return None, None
    case = (await db.execute(
        select(VeterinaryCase).where(VeterinaryCase.farmer_id == session.farmer_id)
        .order_by(VeterinaryCase.created_at.desc()).limit(1))).scalars().first()
    report: Optional[DiseaseReport] = None
    if case is not None and case.report_id:
        report = await db.get(DiseaseReport, case.report_id)
    if report is None:
        report = (await db.execute(
            select(DiseaseReport).where(DiseaseReport.user_id == session.farmer_id)
            .order_by(DiseaseReport.created_at.desc()).limit(1))).scalars().first()
    return case, report


async def handle_case_status(request: Request, db: AsyncSession, session: CallSession) -> VoiceDoc:
    call_router.apply_transition(session, call_router.CASE_STATUS, reason="menu option 3")
    case, report = await recent_case_for(db, session)
    await db.commit()
    if not session.farmer_id:
        warn_ivr("IVR_CASE_STATUS_REFUSED", call_id=session.provider_call_id,
                 call_session=session.id, reason="caller_not_verified")
        await emit(session, "call.completed", {"menu": MENU_CASE_STATUS, "outcome": "caller_not_verified"})
        return VoiceDoc().say_and_hangup(prompts.prompt(session.language, "case_status_unverified"),
                                         language=session.language)
    log_ivr("IVR_CASE_STATUS", call_id=session.provider_call_id, call_session=session.id,
            case_id=case.id if case else None, report_id=report.id if report else None)
    await emit(session, "call.completed",
               {"menu": MENU_CASE_STATUS, "caseId": case.id if case else None,
                "reportId": report.id if report else None})
    return case_status_doc(request, session, case, report)


# ------------------------------------------------------------------------------------------
# Menu handling
# ------------------------------------------------------------------------------------------
async def handle_menu(request: Request, db: AsyncSession, session: CallSession,
                      digits: str) -> Tuple[VoiceDoc, bool]:
    """Apply a main-menu keypress. Returns ``(doc, handled)``; ``handled=False`` means the
    keypress was invalid and the caller should hear the menu again."""
    choice = parse_menu_option(digits)
    if choice is None:
        return VoiceDoc(), False
    session.ivr_menu_option = choice
    call_router.apply_transition(session, call_router.MENU_SELECTED, reason=f"menu digit {choice}")
    await db.commit()
    log_ivr("IVR_MENU_SELECTED", call_id=session.provider_call_id, call_session=session.id,
            menu=choice, emergency=bool(session.is_emergency))
    await emit(session, "call.menu_selected", {"menu": choice})

    if choice == MENU_VETERINARIAN:
        return await start_vet_search(request, db, session), True
    if choice == MENU_CASE_STATUS:
        return await handle_case_status(request, db, session), True
    if choice == MENU_EMERGENCY:
        # An emergency keypress records urgency; it never implies a diagnosis. Risk stays
        # whatever the triage engine computes from the answers the caller actually gives.
        session.is_emergency = True
        await db.commit()
        return await begin_survey(request, db, session, prefix_key="emergency_intro"), True
    # MENU_REPORT (default)
    return await begin_survey(request, db, session, prefix_key="greeting"), True


async def start_vet_search(request: Request, db: AsyncSession, session: CallSession) -> VoiceDoc:
    """PATH A: look for an available veterinarian (existing DispatchEngine) and bridge the
    call; fall back to the report survey (PATH B) when nobody is available."""
    call_router.apply_transition(session, call_router.VET_SEARCH, reason="searching vets")
    await db.commit()
    await emit(session, "call.vet_search_started", {})
    farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
    candidate = await next_vet_candidate(db, session, farmer)
    if candidate is None:
        await db.commit()
        await emit(session, "call.vet_unavailable", {"reason": "no_eligible_vet"})
        return await begin_survey(request, db, session, prefix_key="vet_unavailable")
    return await dial_and_notify(db, session, candidate, request)


async def dial_and_notify(db: AsyncSession, session: CallSession, vet: dict, request: Request) -> VoiceDoc:
    attempts = list(session.vet_attempts or [])
    attempts.append({"vet_id": vet["vet_id"], "phone_tail": (vet.get("phone") or "")[-4:],
                     "result": "dialing"})
    session.vet_attempts = attempts
    session.veterinarian_id = vet["vet_id"]
    call_router.apply_transition(session, call_router.VET_DIALING, reason=f"dialing {vet['vet_id']}")
    vet_user = await db.get(User, vet["vet_id"])
    if vet_user is not None:
        # A notification failure must not cost the farmer the call: log it and dial anyway.
        try:
            from backend.services.notification_service import NotificationService

            await NotificationService.queue(db, channel="IN_APP", template="IVR_CALL_REQUEST",
                                            context={"call_id": session.id}, user=vet_user,
                                            dedup_key=f"ivr-call:{session.id}:{vet['vet_id']}",
                                            require_consent=False)
        except Exception as exc:
            warn_ivr("IVR_NOTIFICATION_FAILED", call_session=session.id, vet_id=vet["vet_id"],
                     error=type(exc).__name__)
    await db.commit()
    await emit(session, "call.vet_found", {"vetId": vet["vet_id"]})
    await emit(session, "call.vet_dialing", {"vetId": vet["vet_id"]})
    log_ivr("IVR_VET_DIALING", call_id=session.provider_call_id, call_session=session.id,
            vet_id=vet["vet_id"])
    return dial_vet_doc(request, session, vet)



__all__ = [
    "IVR_SYSTEM_USER_ID", "MENU_REPORT", "MENU_VETERINARIAN", "MENU_CASE_STATUS", "MENU_EMERGENCY",
    "create_callback_request", "dial_and_notify", "disabled_doc", "emit", "finalize_survey",
    "get_or_create_ivr_system_user", "get_or_create_session", "goodbye_doc", "handle_case_status",
    "handle_menu", "identify_farmer", "log_ivr", "menu_doc", "next_vet_candidate", "normalize_phone",
    "read_webhook", "recent_case_for", "start_vet_search", "survey_doc",
    "warn_ivr", "webhook_token_query", "welcome_doc",
]
