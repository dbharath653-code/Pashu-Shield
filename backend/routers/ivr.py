"""Exotel IVR webhooks — the telephony entry point for Pashu Shield.

Three endpoints, exactly the ones the Exotel integration needs:

``POST /api/v1/ivr/incoming``
    The **ExoML application URL** configured on the ExoPhone (dashboard → App Bazaar →
    your app → application URL). Exotel POSTs here when a farmer's call is answered and
    expects an ExoML ``<Response>`` back. Creates the ``CallSession`` (idempotent on the
    Exotel ``CallSid``), identifies the caller by phone, returns welcome + language menu.

``POST /api/v1/ivr/input``
    Every ExoML ``action`` callback during the call. ``?step=`` selects the handler:
    ``language`` (language digits) · ``menu`` (main menu) · ``survey`` (``&q=<question>``)
    · ``vet_dial`` (outcome of the bridged veterinarian leg, ``DialCallStatus``).

``POST /api/v1/ivr/status``
    The Exotel **StatusCallback** (terminal/answered). Telemetry only: it records status,
    duration and the private recording URL and returns an empty document so it can never
    alter a live call.

Security model (Exotel does not sign webhooks — see ``docs/EXOTEL_SETUP.md``):
shared ``EXOTEL_WEBHOOK_SECRET`` in the action URL, ``CallSid`` correlation against a
session an already-verified ``/incoming`` created, optional authenticated CallSid
verification, per-call rate limiting, HTTPS in production.

Response contract
-----------------
    200 + ExoML   normal flow, IVR disabled, and any downstream failure (the farmer always
                  hears a polite message instead of dead air)
    400           malformed webhook / missing ``CallSid``
    401           webhook could not be trusted
    404           ``CallSid`` does not match a call session on this server
    409           follow-up for a call that has no survey
    429           rate limited
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import CallSession, IVRSurvey, IVRSurveyResponse, User
from backend.services.ivr import prompts
from backend.services.ivr.question_flow import QUESTIONS
from backend.services.ivr.survey_engine import SurveyEngine
from backend.services.rate_limit import enforce
from backend.services.telephony import WebhookVerificationError, get_provider
from backend.services.telephony import call_router
from backend.services.telephony.exoml import action_url
from backend.services.telephony.markup import VoiceDoc, empty_voice_response, voice_response
from backend.services.telephony.webhook_service import (begin_survey, create_callback_request,
                                                        dial_and_notify, disabled_doc, emit,
                                                        finalize_survey,
                                                        get_or_create_ivr_system_user,
                                                        get_or_create_session, goodbye_doc,
                                                        handle_menu, identify_farmer, log_ivr,
                                                        menu_doc, next_vet_candidate,
                                                        read_webhook, survey_doc, warn_ivr,
                                                        welcome_doc)

logger = logging.getLogger("pashu_shield.telephony")

router = APIRouter(prefix="/ivr", tags=["IVR (Exotel ExoML Webhooks)"])


# ------------------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------------------
def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "INVALID_WEBHOOK",
                                                  "message": "Webhook could not be verified"})


def _apology(language: str = "en") -> object:
    """200 + a polite message: a farmer must never be left on a silent line because of a
    server-side failure. The technical detail is in the logs, never in the response."""
    return voice_response(VoiceDoc().say_and_hangup(prompts.prompt(language, "ivr_disabled"),
                                                    language=language))


async def _load_session(db: AsyncSession, call_id: str) -> CallSession:
    session = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_id))).scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND",
                                                     "message": "Unknown call id"})
    return session


async def _read(request: Request):
    """Verify, rate-limit and parse one webhook. Returns ``(params, call_id)``."""
    try:
        params, call_id = await read_webhook(request)
    except WebhookVerificationError:
        raise _unauthorized()
    if call_id == "-":
        warn_ivr("IVR_WEBHOOK_MALFORMED", reason="missing_call_id", path=request.url.path)
        raise HTTPException(status_code=400, detail={"code": "MISSING_CALL_ID",
                                                     "message": "CallSid is required"})
    # Rate limit per *call*, not per IP: every Exotel webhook arrives from Exotel's own
    # egress range, so an IP bucket would throttle every farmer at once. A real IVR call
    # produces a couple of dozen webhooks; this bounds a stuck/malicious flow.
    try:
        await enforce("ivr_call", call_id[:64])
    except HTTPException:
        raise
    except Exception as exc:  # limiter outage must not take the helpline down
        warn_ivr("IVR_RATE_LIMIT_BACKEND_ERROR", error=type(exc).__name__, call_id=call_id)
    return params, call_id


async def _resolve_reporter(db: AsyncSession, session: CallSession) -> User:
    reporter = await db.get(User, session.farmer_id) if session.farmer_id else None
    return reporter if reporter is not None else await get_or_create_ivr_system_user(db)


# ------------------------------------------------------------------------------------------
# 1) Inbound call: PHONE -> EXOTEL -> FASTAPI -> ExoML welcome
# ------------------------------------------------------------------------------------------
@router.api_route("/incoming", methods=["POST", "GET"])
async def incoming_call(request: Request):
    params, call_id = await _read(request)

    if not settings.IVR_ENABLED:
        log_ivr("IVR_CALL_REJECTED", call_id=call_id, reason="ivr_disabled")
        return voice_response(disabled_doc())

    try:
        async with AsyncSessionLocal() as db:
            session, created = await get_or_create_session(db, params, call_id)
            if created:
                farmer = await identify_farmer(db, session)
                if farmer is not None and farmer.district:
                    session.district = farmer.district
                call_router.apply_transition(session, call_router.IDENTIFIED,
                                             reason="caller identified" if farmer else "unknown caller")
                await db.commit()
                log_ivr("IVR_SESSION_CREATED", call_id=call_id, call_session=session.id,
                        provider=session.provider, caller_known=farmer is not None,
                        caller_masked=(session.caller_phone or "")[-4:] or None,
                        farmer_id=session.farmer_id, simulated=session.is_simulated)
                await emit(session, "call.started", {"created": True, "callerKnown": farmer is not None})
            else:
                # Exotel retried the webhook: idempotent — never a second session or report.
                await db.commit()
                log_ivr("IVR_CALL_RECEIVED", call_id=call_id, call_session=session.id,
                        duplicate=True, status=session.status)
    except HTTPException:
        raise
    except Exception:
        logger.exception("inbound call handling failed", extra={"fields": {"call_id": call_id}})
        warn_ivr("IVR_CALL_FAILED", call_id=call_id, reason="inbound_error")
        return _apology()

    log_ivr("IVR_CALL_RECEIVED", call_id=call_id, call_session=session.id)
    return voice_response(welcome_doc(request))


# ------------------------------------------------------------------------------------------
# 2) Mid-call input: language, main menu, survey answers, veterinarian dial result
# ------------------------------------------------------------------------------------------
@router.api_route("/input", methods=["POST", "GET"])
async def ivr_input(request: Request):
    params, call_id = await _read(request)
    provider = get_provider()
    step = (params.get("step") or "").strip().lower()
    digits = provider.get_digits(params)

    try:
        async with AsyncSessionLocal() as db:
            session = await _load_session(db, call_id)
            log_ivr("IVR_INPUT_RECEIVED", call_id=call_id, call_session=session.id,
                    step=step or "language", question=params.get("q") or None,
                    digits=digits or None, dial_status=provider.get_dial_result(params) or None)

            if step == "vet_dial":
                doc = await _handle_vet_dial(request, db, session, provider.get_dial_result(params))
            elif step == "survey":
                doc = await _handle_survey_answer(request, db, session, digits)
            elif step == "menu":
                doc = await _handle_menu_step(request, db, session, digits)
            else:
                doc = await _handle_language(request, db, session, digits)
            return voice_response(doc)
    except HTTPException:
        raise
    except Exception:
        logger.exception("ivr input handling failed",
                         extra={"fields": {"call_id": call_id, "step": step}})
        warn_ivr("IVR_CALL_FAILED", call_id=call_id, reason="input_error", step=step)
        return _apology()


async def _handle_language(request: Request, db: AsyncSession, session: CallSession, digits: str) -> VoiceDoc:
    language = prompts.LANGUAGE_DIGITS.get(digits)
    if language is None:
        if not digits:
            # Gather timed out with no keypress: repeat the welcome/menu once, then hang up.
            return welcome_doc(request)
        return (VoiceDoc()
                .say(prompts.prompt(settings.IVR_DEFAULT_LANGUAGE, "invalid"), language="en")
                .gather(prompts.LANGUAGE_MENU, action_url(request, "/api/v1/ivr/input", "step=language"),
                        language="en", num_digits=1, timeout=8)
                .hangup())
    session.language = language
    call_router.apply_transition(session, call_router.LANGUAGE_SELECTED, reason=f"digit {digits}")
    await db.commit()
    await emit(session, "call.language_selected", {"language": language})
    return menu_doc(request, language)


async def _handle_menu_step(request: Request, db: AsyncSession, session: CallSession, digits: str) -> VoiceDoc:
    doc, handled = await handle_menu(request, db, session, digits)
    if handled:
        return doc
    # Invalid key: re-ask. The returned document itself repeats the menu once and hangs up,
    # and the per-call webhook rate limit bounds how often this can happen.
    warn_ivr("IVR_MENU_INVALID", call_id=session.provider_call_id, call_session=session.id,
             digits=digits or None)
    return (VoiceDoc()
            .say(prompts.prompt(session.language, "invalid"), language=session.language)
            .gather(prompts.prompt(session.language, "main_menu"),
                    action_url(request, "/api/v1/ivr/input", "step=menu"),
                    language=session.language, num_digits=1, timeout=8)
            .hangup())


async def _handle_survey_answer(request: Request, db: AsyncSession, session: CallSession,
                                digits: str) -> VoiceDoc:
    survey = await db.get(IVRSurvey, session.ivr_survey_id) if session.ivr_survey_id else None
    if survey is None:
        survey = (await db.execute(select(IVRSurvey)
                                   .where(IVRSurvey.call_session_id == session.id))).scalars().first()
    if survey is None:
        raise HTTPException(status_code=409, detail={"code": "NO_SURVEY",
                                                     "message": "No active survey for this call"})

    # Idempotent replay for a finished survey: re-acknowledge, change nothing.
    if survey.status != "IN_PROGRESS":
        return goodbye_doc(survey.language or settings.IVR_DEFAULT_LANGUAGE)

    language = survey.language or settings.IVR_DEFAULT_LANGUAGE
    question_key = survey.current_question
    if question_key in (None, "done"):
        question_key = "confirm"
        survey.current_question = "confirm"
    question = QUESTIONS[question_key]

    accepted, normalized, raw_input = question.validate(digits)

    if not accepted:
        outcome = SurveyEngine.handle_input(survey, raw_input, valid=False)
        await db.commit()
        if outcome == "exhausted" and question.required and not question.allow_unknown:
            # A required answer cannot be collected honestly -> abort and queue a callback.
            survey.status = "ABANDONED"
            reporter = await _resolve_reporter(db, session)
            call_router.apply_transition(session, call_router.CALLBACK_REQUESTED,
                                         reason="required answer exhausted")
            cb = await create_callback_request(db, session, None, reporter, survey=survey,
                                               reason="invalid_input")
            session.last_error = f"invalid_input:{question_key}"
            await db.commit()
            await emit(session, "call.callback_requested",
                       {"callbackId": cb.id, "reason": "invalid_input"})
            warn_ivr("IVR_CALL_FAILED", call_id=session.provider_call_id, call_session=session.id,
                     reason="invalid_input", question=question_key)
            return VoiceDoc().say_and_hangup(prompts.prompt(language, "survey_aborted"), language=language)
        prefix = prompts.prompt(language, "invalid") + (
            prompts.prompt(language, "too_many_attempts") if outcome == "exhausted" else "")
        return survey_doc(request, language, survey.current_question, prefix=prefix)

    # ---- accepted answer -------------------------------------------------------------------
    if question_key == "confirm":
        if normalized == "RESTART":
            rows = (await db.execute(select(IVRSurveyResponse)
                                     .where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
            for row in rows:
                await db.delete(row)
            SurveyEngine.restart(survey)
            await db.commit()
            return survey_doc(request, language, "species", prefix=prompts.prompt(language, "greeting"))
        if normalized == "CANCEL":
            survey.status = "CANCELLED"
            reporter = await _resolve_reporter(db, session)
            call_router.apply_transition(session, call_router.CALLBACK_REQUESTED,
                                         reason="caller cancelled survey")
            cb = await create_callback_request(db, session, None, reporter, survey=survey,
                                               reason="cancelled")
            await db.commit()
            await emit(session, "call.callback_requested", {"callbackId": cb.id, "reason": "cancelled"})
            return VoiceDoc().say_and_hangup(prompts.prompt(language, "cancelled"), language=language)
        # CONFIRM -> the existing DiseaseReport pipeline (triage -> case -> dispatch -> alerts).
        call_router.apply_transition(session, call_router.CONFIRMATION, reason="caller confirmed")
        await db.commit()
        return await finalize_survey(db, session, survey)

    await SurveyEngine.record_answer(db, survey, question_key, raw_input, normalized)
    SurveyEngine.handle_input(survey, raw_input, valid=True)
    await db.commit()
    await emit(session, "call.survey_answered", {"question": question_key})
    return survey_doc(request, language, survey.current_question)


async def _handle_vet_dial(request: Request, db: AsyncSession, session: CallSession,
                           dial_status: str) -> VoiceDoc:
    attempts = list(session.vet_attempts or [])
    if attempts:
        attempts[-1] = {**attempts[-1], "result": dial_status or "unknown"}
        session.vet_attempts = attempts

    if dial_status == "completed":
        vet_id = attempts[-1].get("vet_id") if attempts else None
        if vet_id:
            session.veterinarian_id = vet_id
        call_router.apply_transition(session, call_router.VET_CONNECTED, reason="vet answered")
        call_router.apply_transition(session, call_router.BRIDGED, reason="farmer<->vet conversation")
        session.recording_status = "IN_PROGRESS" if settings.CALL_RECORDING_ENABLED else "DISABLED"
        await db.commit()
        await emit(session, "call.vet_connected", {"vetId": session.veterinarian_id})
        log_ivr("IVR_VET_CONNECTED", call_id=session.provider_call_id, call_session=session.id,
                vet_id=session.veterinarian_id)
        return goodbye_doc(session.language)

    # busy / no-answer / failed / canceled / timeout -> next veterinarian, else the survey.
    log_ivr("IVR_VET_UNAVAILABLE", call_id=session.provider_call_id, call_session=session.id,
            dial_status=dial_status or "unknown")
    await emit(session, "call.vet_unavailable", {"attemptResult": dial_status})
    farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
    nxt = await next_vet_candidate(db, session, farmer)
    if nxt is not None:
        return await dial_and_notify(db, session, nxt, request)
    call_router.apply_transition(session, call_router.VET_SEARCH, reason="exhausted vet attempts")
    await db.commit()
    return await begin_survey(request, db, session, prefix_key="vet_unavailable")


# ------------------------------------------------------------------------------------------
# 3) StatusCallback (telemetry only — returns an empty document, never alters a live call)
# ------------------------------------------------------------------------------------------
@router.api_route("/status", methods=["POST", "GET"])
async def call_status(request: Request):
    params, call_id = await _read(request)
    provider = get_provider()
    status = provider.get_provider_status(params)
    recording_url = provider.get_recording_url(params)
    duration = params.get("ConversationDuration") or params.get("Duration") or params.get("CallDuration")

    try:
        async with AsyncSessionLocal() as db:
            session = await _load_session(db, call_id)
            session.last_status = status or session.last_status
            target = call_router.PROVIDER_STATUS_MAP.get(status)
            if status == "in-progress" and session.answered_at is None:
                session.answered_at = datetime.utcnow()
            if target:
                call_router.apply_transition(session, target, reason=f"provider status {status}")
            if target in (call_router.COMPLETED, call_router.FAILED) and session.ended_at is None:
                session.ended_at = datetime.utcnow()
            if status in ("failed", "busy", "no-answer", "canceled") and not session.last_error:
                session.last_error = f"provider:{status}"

            # The recording URL stays private: it is fetched only through the RBAC-checked,
            # audited dashboard endpoint, never served publicly.
            if recording_url and session.recording_url != recording_url:
                session.recording_url = recording_url[:512]
                session.recording_status = "COMPLETED"
                try:
                    session.recording_duration = int(duration) if duration else session.recording_duration
                except ValueError:
                    pass
                from backend.services.jobs import enqueue

                await enqueue(db, "call.process_recording", {"call_session_id": session.id},
                              dedup_key=f"rec:{session.id}")
            await db.commit()

            if target in (call_router.COMPLETED, call_router.FAILED):
                await emit(session, "call.completed",
                           {"providerStatus": status, "duration": duration, "outcome": target})
                log_ivr("IVR_CALL_COMPLETED" if target == call_router.COMPLETED else "IVR_CALL_FAILED",
                        call_id=call_id, call_session=session.id, provider_status=status,
                        duration=duration, report_id=session.disease_report_id,
                        has_recording=bool(session.recording_url))
            else:
                log_ivr("IVR_CALL_STATUS", call_id=call_id, call_session=session.id,
                        provider_status=status, state=session.status)
    except HTTPException:
        raise
    except Exception:
        logger.exception("status callback handling failed", extra={"fields": {"call_id": call_id}})
        warn_ivr("IVR_CALL_FAILED", call_id=call_id, reason="status_callback_error")
    return empty_voice_response()


__all__ = ["router", "incoming_call", "ivr_input", "call_status"]
