"""Twilio voice webhooks (unauthenticated — secured by provider signature validation).

POST /telephony/inbound   – real inbound call: welcome + language selection (TwiML)
POST /telephony/ivr       – language digits, vet <Dial> action results, step routing
POST /telephony/survey    – DTMF/speech answers for the survey questions
POST /telephony/status    – provider CallStatus callbacks (idempotent state tracking)
POST /telephony/recording – recording ready callback (private URL, audited access only)

Every endpoint answers with valid TwiML (`application/xml`), never JSON.
Correlation: logs and audit rows carry CallSid + CallSession id.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.models import CallSession, IVRSurvey, IVRSurveyResponse, User
from backend.services.ivr import prompts
from backend.services.ivr.question_flow import QUESTIONS
from backend.services.ivr.survey_engine import SurveyEngine
from backend.services.telephony import WebhookVerificationError
from backend.services.telephony import call_router
from backend.services.telephony.twiml import (gather_dtmf, say, twiml_response)
from backend.services.telephony.webhook_service import (begin_survey_twiml, create_callback_request,
                                                        dial_vet_twiml, disabled_twiml, emit,
                                                        finalize_survey, get_or_create_session,
                                                        get_or_create_ivr_system_user,
                                                        identify_farmer, next_vet_candidate,
                                                        read_webhook, survey_twiml, welcome_twiml)

logger = logging.getLogger("pashu_shield.telephony")

router = APIRouter(prefix="/telephony", tags=["Telephony IVR Webhooks (Twilio)"])


def _verification_error(request: Request) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "INVALID_WEBHOOK_SIGNATURE",
                                                  "message": "Webhook signature verification failed"})


def _empty_twiml() -> Response:
    return Response(content="<Response></Response>", media_type="application/xml")


async def _load_session(db: AsyncSession, call_sid: str) -> CallSession:
    session = (await db.execute(select(CallSession).where(CallSession.provider_call_id == call_sid))).scalars().first()
    if session is None:
        raise HTTPException(status_code=404, detail={"code": "CALL_NOT_FOUND", "message": "Unknown CallSid"})
    return session


# ------------------------------------------------------------------------------------------
# 1) Real inbound call — the first milestone: PHONE -> TWILIO -> FASTAPI -> TwiML welcome
# ------------------------------------------------------------------------------------------
@router.post("/inbound")
async def inbound_call(request: Request):
    try:
        params, call_sid = await read_webhook(request)
    except WebhookVerificationError:
        raise _verification_error(request)

    if not settings.IVR_ENABLED:
        logger.info("inbound call rejected: IVR disabled", extra={"fields": {"call_sid": call_sid}})
        return disabled_twiml(request)

    async with AsyncSessionLocal() as db:
        session, created = await get_or_create_session(db, params, call_sid)
        if created:
            farmer = await identify_farmer(db, session)
            if farmer is not None and farmer.district:
                session.district = farmer.district
            call_router.apply_transition(session, call_router.IDENTIFIED,
                                         reason="farmer identified" if farmer else "unknown caller")
            await db.commit()
            logger.info("inbound call session created", extra={"fields": {
                "call_sid": call_sid, "call_session": session.id,
                "caller_masked": (session.caller_phone or "")[-4:] or None,
                "farmer_id": session.farmer_id}})
            await emit(session, "call.started", {"created": True})
        else:
            await db.commit()
            logger.info("duplicate inbound webhook (idempotent)", extra={"fields": {
                "call_sid": call_sid, "call_session": session.id, "status": session.status}})

    # Welcome message + language selection gather (Phase 1 + 2).
    return welcome_twiml(request, language=session.language)


# ------------------------------------------------------------------------------------------
# 2) Language selection + veterinarian <Dial> action + step routing
# ------------------------------------------------------------------------------------------
@router.post("/ivr")
async def ivr_step(request: Request):
    try:
        params, call_sid = await read_webhook(request)
    except WebhookVerificationError:
        raise _verification_error(request)

    async with AsyncSessionLocal() as db:
        session = await _load_session(db, call_sid)
        step = (params.get("step") or "").strip()
        digits = (params.get("Digits") or "").strip()

        # ---- PATH A: result of the <Dial> to a veterinarian --------------------------------
        if step == "vet_dial":
            dial_status = (params.get("DialCallStatus") or "").strip().lower()
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
                await emit(session, "call.vet_connected", {"vetId": session.veterinarian_id,
                                                           "dialDuration": params.get("DialCallDuration")})
                from backend.services.telephony.twiml import VoiceResponse
                vr = VoiceResponse()
                say(vr, prompts.prompt(session.language, "call_bye"), language=session.language)
                vr.hangup()
                return twiml_response(vr)

            # busy / no-answer / failed / timeout / rejected -> next vet or survey
            logger.info("vet dial attempt finished without connection", extra={
                "fields": {"call_session": session.id, "call_sid": call_sid, "dial_status": dial_status}})
            await emit(session, "call.vet_unavailable", {"attemptResult": dial_status})
            farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
            nxt = await next_vet_candidate(db, session, farmer)
            if nxt is not None:
                return await dial_and_notify(db, session, nxt, request)
            call_router.apply_transition(session, call_router.VET_SEARCH, reason="exhausted vet attempts")
            await db.commit()
            return await begin_survey_twiml(request, db, session, prefix_key="vet_unavailable")

        # ---- explicit step routing -----------------------------------------------------------
        if step == "survey":
            return await begin_survey_twiml(request, db, session, prefix_key="vet_unavailable")

        # ---- language selection (default) ----------------------------------------------------
        if digits:
            language = prompts.LANGUAGE_DIGITS.get(digits)
            if language is None:
                # invalid language digit -> re-gather the menu
                from backend.services.telephony.twiml import VoiceResponse
                vr = VoiceResponse()
                say(vr, prompts.prompt(settings.IVR_DEFAULT_LANGUAGE, "invalid"), language="en")
                gather = gather_dtmf(request, "/api/v1/telephony/ivr", prompts.LANGUAGE_MENU, language="en",
                                     num_digits=1, timeout=8)
                vr.append(gather)
                vr.hangup()
                return twiml_response(vr)
            session.language = language
            call_router.apply_transition(session, call_router.LANGUAGE_SELECTED, reason=f"digit {digits}")
            await db.commit()
            await emit(session, "call.language_selected", {"language": language})

            # Check veterinarian availability (existing dispatch eligibility engine).
            call_router.apply_transition(session, call_router.VET_SEARCH, reason="searching vets")
            await db.commit()
            await emit(session, "call.vet_search_started", {})
            farmer = await db.get(User, session.farmer_id) if session.farmer_id else None
            candidate = await next_vet_candidate(db, session, farmer)
            if candidate is not None:
                return await dial_and_notify(db, session, candidate, request)
            await db.commit()
            await emit(session, "call.vet_unavailable", {"reason": "no_eligible_vet"})
            return await begin_survey_twiml(request, db, session, prefix_key="vet_unavailable")

        # No digits (timeout/redirect) -> repeat the welcome menu.
        return welcome_twiml(request, language=session.language)


async def dial_and_notify(db: AsyncSession, session: CallSession, vet: dict, request: Request):
    from backend.services.notification_service import NotificationService
    attempts = list(session.vet_attempts or [])
    attempts.append({"vet_id": vet["vet_id"], "phone_tail": (vet.get("phone") or "")[-4:],
                     "result": "dialing"})
    session.vet_attempts = attempts
    session.veterinarian_id = vet["vet_id"]
    call_router.apply_transition(session, call_router.VET_DIALING, reason=f"dialing {vet['vet_id']}")
    vet_user = await db.get(User, vet["vet_id"])
    if vet_user is not None:
        await NotificationService.queue(db, channel="IN_APP", template="IVR_CALL_REQUEST",
                                        context={"call_id": session.id}, user=vet_user,
                                        dedup_key=f"ivr-call:{session.id}:{vet['vet_id']}", require_consent=False)
    await db.commit()
    await emit(session, "call.vet_found", {"vetId": vet["vet_id"]})
    await emit(session, "call.vet_dialing", {"vetId": vet["vet_id"]})
    return dial_vet_twiml(request, session, vet)


# ------------------------------------------------------------------------------------------
# 3) Survey DTMF / speech answers
# ------------------------------------------------------------------------------------------
@router.post("/survey")
async def survey_answer(request: Request):
    try:
        params, call_sid = await read_webhook(request)
    except WebhookVerificationError:
        raise _verification_error(request)

    async with AsyncSessionLocal() as db:
        session = await _load_session(db, call_sid)
        survey = await db.get(IVRSurvey, session.ivr_survey_id) if session.ivr_survey_id else None
        if survey is None:
            survey = (await db.execute(select(IVRSurvey).where(IVRSurvey.call_session_id == session.id))).scalars().first()
        if survey is None:
            raise HTTPException(status_code=409, detail={"code": "NO_SURVEY", "message": "No active survey for this call"})

        # Idempotent replay of a webhook for an already-finished survey: re-acknowledge
        # without advancing state or creating anything.
        if survey.status != "IN_PROGRESS":
            language = survey.language or settings.IVR_DEFAULT_LANGUAGE
            from backend.services.telephony.twiml import VoiceResponse
            vr = VoiceResponse()
            say(vr, prompts.prompt(language, "call_bye"), language=language)
            vr.hangup()
            return twiml_response(vr)

        question_key = survey.current_question
        if question_key in (None, "done"):
            question_key = "confirm"
            survey.current_question = "confirm"
        question = QUESTIONS[question_key]
        language = survey.language or settings.IVR_DEFAULT_LANGUAGE

        raw = (params.get("Digits") or "").strip()
        speech = (params.get("SpeechResult") or "").strip()
        if not raw and speech:
            raw = speech

        accepted, normalized, raw_input = question.validate(raw)

        if not accepted:
            outcome = SurveyEngine.handle_input(survey, raw_input, valid=False)
            await db.commit()
            if outcome == "exhausted" and question.required and not question.allow_unknown:
                # Cannot collect a required answer honestly -> abort to callback queue.
                survey.status = "ABANDONED"
                await db.commit()
                reporter = await db.get(User, session.farmer_id) if session.farmer_id else None
                if reporter is None:
                    reporter = await get_or_create_ivr_system_user(db)
                call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="required answer exhausted")
                cb = await create_callback_request(db, session, None, reporter, survey=survey)
                session.last_error = f"invalid_input:{question_key}"
                await db.commit()
                await emit(session, "call.callback_requested", {"callbackId": cb.id, "reason": "invalid_input"})
                from backend.services.telephony.twiml import VoiceResponse
                vr = VoiceResponse()
                say(vr, prompts.prompt(language, "survey_aborted"), language=language)
                vr.hangup()
                return twiml_response(vr)
            prefix = prompts.prompt(language, "invalid") + (
                prompts.prompt(language, "too_many_attempts") if outcome == "exhausted" else "")
            return survey_twiml(request, language, survey.current_question, prefix=prefix)

        # ---- accepted answer ------------------------------------------------------------------
        if question_key == "confirm":
            decision = normalized
            if decision == "RESTART":
                rows = (await db.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
                for r in rows:
                    await db.delete(r)
                SurveyEngine.restart(survey)
                await db.commit()
                return survey_twiml(request, language, "species",
                                    prefix=prompts.prompt(language, "greeting"))
            if decision == "CANCEL":
                survey.status = "CANCELLED"
                reporter = await db.get(User, session.farmer_id) if session.farmer_id else None
                if reporter is None:
                    reporter = await get_or_create_ivr_system_user(db)
                call_router.apply_transition(session, call_router.CALLBACK_REQUESTED, reason="farmer cancelled survey")
                cb = await create_callback_request(db, session, None, reporter, survey=survey)
                await db.commit()
                await emit(session, "call.callback_requested", {"callbackId": cb.id, "reason": "cancelled"})
                from backend.services.telephony.twiml import VoiceResponse
                vr = VoiceResponse()
                say(vr, prompts.prompt(language, "cancelled"), language=language)
                vr.hangup()
                return twiml_response(vr)

            # CONFIRM -> existing DiseaseReport pipeline (report_service: triage/case/alert/callback)
            call_router.apply_transition(session, call_router.CONFIRMATION, reason="farmer confirmed")
            await db.commit()
            return await finalize_survey(db, session, survey)

        await SurveyEngine.record_answer(db, survey, question_key, raw_input, normalized)
        SurveyEngine.handle_input(survey, raw_input, valid=True)
        await db.commit()
        await emit(session, "call.survey_answered", {"question": question_key})
        return survey_twiml(request, language, survey.current_question,
                            prefix="" )


# ------------------------------------------------------------------------------------------
# 4) Call status callbacks (idempotent; drives answered/ended/failed tracking)
# ------------------------------------------------------------------------------------------
@router.post("/status")
async def call_status(request: Request):
    try:
        params, call_sid = await read_webhook(request)
    except WebhookVerificationError:
        # Status callbacks are telemetry; reject loudly but never crash the flow.
        raise _verification_error(request)

    provider_status = (params.get("CallStatus") or params.get("DialCallStatus") or "").strip().lower()
    duration = params.get("CallDuration") or params.get("Duration")
    async with AsyncSessionLocal() as db:
        session = await _load_session(db, call_sid)
        session.last_status = provider_status or session.last_status
        target = call_router.PROVIDER_STATUS_MAP.get(provider_status)
        from datetime import datetime
        if provider_status == "in-progress" and session.answered_at is None:
            session.answered_at = datetime.utcnow()
        if target:
            call_router.apply_transition(session, target, reason=f"provider status {provider_status}")
        if target in (call_router.COMPLETED, call_router.FAILED) and session.ended_at is None:
            session.ended_at = datetime.utcnow()
        if provider_status in ("failed", "busy", "no-answer", "canceled") and not session.last_error:
            session.last_error = f"provider:{provider_status}"
        await db.commit()
        if target in (call_router.COMPLETED, call_router.FAILED):
            await emit(session, "call.completed", {"providerStatus": provider_status,
                                                   "duration": duration, "outcome": target})
        logger.info("call status callback", extra={"fields": {
            "call_session": session.id, "call_sid": call_sid, "provider_status": provider_status,
            "state": session.status}})
    return _empty_twiml()


# ------------------------------------------------------------------------------------------
# 5) Recording callback (URL stays private: fetched only via RBAC-checked audited endpoint)
# ------------------------------------------------------------------------------------------
@router.post("/recording")
async def recording_callback(request: Request):
    try:
        params, call_sid = await read_webhook(request)
    except WebhookVerificationError:
        raise _verification_error(request)

    recording_url = params.get("RecordingUrl") or ""
    recording_sid = params.get("RecordingSid") or ""
    duration = params.get("RecordingDuration")
    async with AsyncSessionLocal() as db:
        session = await _load_session(db, call_sid)
        if recording_url.startswith("https://"):
            session.recording_url = recording_url[:512]
            session.recording_sid = recording_sid or session.recording_sid
            try:
                session.recording_duration = int(duration) if duration else session.recording_duration
            except ValueError:
                pass
            session.recording_status = "COMPLETED"
            await db.commit()
            from backend.services.jobs import enqueue
            await enqueue(db, "call.process_recording", {"call_session_id": session.id},
                          dedup_key=f"rec:{session.id}")
            await db.commit()
            logger.info("recording stored (private)", extra={"fields": {
                "call_session": session.id, "call_sid": call_sid, "duration": duration}})
    return _empty_twiml()
