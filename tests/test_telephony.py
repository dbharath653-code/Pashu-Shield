"""IVR / Twilio telephony test-suite.

Covers (spec §25):
  1 inbound webhook, 2 signature validation, 3 duplicate webhook, 4 language selection,
  5 DTMF survey, 6 invalid DTMF, 7 survey confirmation, 8 DiseaseReport creation,
  9 existing triage integration, 10 vet available, 11 vet no-answer, 12 vet busy,
  13 multiple vet attempts, 14 callback creation, 15 call completion, 16 Twilio failure,
  17 unauthorized dashboard access, 18 MockTelephonyProvider complete flow,
 plus the required end-to-end integration test:
  INBOUND -> LANGUAGE -> SURVEY -> REPORT -> TRIAGE -> CALLBACK
"""
import os
import uuid

import pytest
from twilio.request_validator import RequestValidator

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio

TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
BASE = os.environ["PUBLIC_API_BASE_URL"]  # http://test
WELCOME = "Welcome to Pashu Shield livestock health helpline."

# Demo farmer phone (registered) -> identifies DEMO-FARMER-001, district Pune
REGISTERED_FARMER_FROM = "+919000000001"
UNKNOWN_FROM = "+919876543210"


def sign(url: str, params: dict, token: str = TOKEN) -> str:
    return RequestValidator(token).compute_signature(url, params)


def tw_headers(url: str, params: dict, token: str = TOKEN) -> dict:
    return {"X-Twilio-Signature": sign(url, params, token)}


async def post_twiml(client, path: str, params: dict, *, query: str = "", token: str = TOKEN,
                     signature: str = None, headers: dict = None):
    """POST a signed Twilio form webhook; returns (response, twiml_text)."""
    url = BASE + path + (f"?{query}" if query else "")
    h = {"X-Twilio-Signature": signature if signature is not None else sign(url, params, token)}
    if headers:
        h.update(headers)
    res = await client.post(path + (f"?{query}" if query else ""), data=params, headers=h)
    return res


def assert_twiml(res, *needles: str):
    assert res.status_code == 200, res.text
    assert "xml" in res.headers.get("content-type", ""), res.headers
    body = res.text
    assert "<Response" in body[:300], body[:200]
    for n in needles:
        assert n in body, f"missing {n!r} in {body[:800]}"
    return body


async def db():
    from backend.database import AsyncSessionLocal
    return AsyncSessionLocal()


# ------------------------------------------------------------------------------------------
# 1 + 2: inbound webhook & signature validation
# ------------------------------------------------------------------------------------------
async def test_inbound_returns_welcome_twiml(client):
    params = {"CallSid": f"CA{uuid.uuid4().hex[:14]}", "From": UNKNOWN_FROM, "To": "+15005550006"}
    res = await post_twiml(client, "/api/v1/telephony/inbound", params)
    body = assert_twiml(res, WELCOME, "<Gather")
    # language menu present (Phase 2)
    assert "Press 1 for English" in body
    assert 'action="' in body


async def test_webhook_signature_required_and_validated(client):
    params = {"CallSid": f"CA{uuid.uuid4().hex[:14]}", "From": UNKNOWN_FROM}
    # missing signature -> 401
    res = await client.post("/api/v1/telephony/inbound", data=params)
    assert res.status_code == 401
    # wrong token -> 401
    url = BASE + "/api/v1/telephony/inbound"
    res = await client.post("/api/v1/telephony/inbound", data=params,
                            headers={"X-Twilio-Signature": sign(url, params, "wrong-token")})
    assert res.status_code == 401
    # correct signature -> 200 TwiML
    res = await post_twiml(client, "/api/v1/telephony/inbound", params)
    assert res.status_code == 200
    # validation disabled -> unsigned accepted (then restore)
    from backend.config import settings
    settings.TWILIO_VALIDATE_WEBHOOK = False
    try:
        res = await client.post("/api/v1/telephony/inbound", data=params)
        assert res.status_code == 200
    finally:
        settings.TWILIO_VALIDATE_WEBHOOK = True


# ------------------------------------------------------------------------------------------
# 3: duplicate webhook idempotency
# ------------------------------------------------------------------------------------------
async def test_duplicate_inbound_webhook_is_idempotent(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    params = {"CallSid": sid, "From": UNKNOWN_FROM}
    r1 = await post_twiml(client, "/api/v1/telephony/inbound", params)
    assert_twiml(r1, WELCOME)
    r2 = await post_twiml(client, "/api/v1/telephony/inbound", params)
    assert_twiml(r2, WELCOME)
    from sqlalchemy import func, select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        n = (await sdb.execute(select(func.count()).where(CallSession.provider_call_id == sid))).scalar()
    assert n == 1


# ------------------------------------------------------------------------------------------
# 4: language selection
# ------------------------------------------------------------------------------------------
async def test_language_selection_starts_survey_for_unknown_caller(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
    res = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
    body = assert_twiml(res, "What animal is affected", "<Gather")
    assert 'action="/api/v1/telephony/survey"' in body or "/api/v1/telephony/survey" in body

    # stored language
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.language == "en"
        assert session.status == "SURVEY"


async def test_invalid_language_digit_reprompts(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
    res = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "9"})
    assert_twiml(res, "Press 1 for English")


async def test_hindi_language_selection(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
    res = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "2"})
    body = assert_twiml(res)  # survey prompt in Hindi fallback (hi table)
    assert "कौन सा पशु प्रभावित है" in body
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.language == "hi"


# ------------------------------------------------------------------------------------------
# 5 + 6 + 7: DTMF survey, invalid DTMF, confirmation
# ------------------------------------------------------------------------------------------
async def start_survey(client, caller=UNKNOWN_FROM, language_digit="1"):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": caller})
    res = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": language_digit})
    return sid, res


async def survey_answer(client, sid, digits=None, speech=None, query=""):
    params = {"CallSid": sid}
    if digits is not None:
        params["Digits"] = digits
    if speech is not None:
        params["SpeechResult"] = speech
    return await post_twiml(client, "/api/v1/telephony/survey", params, query=query)


async def test_invalid_dtmf_reasks_same_question(client):
    sid, _ = await start_survey(client)
    res = await survey_answer(client, sid, digits="9", query="q=species")  # invalid species key
    body = assert_twiml(res, "What animal is affected")
    assert "not a valid option" in body


async def test_survey_answers_persist_and_advance(client):
    sid, _ = await start_survey(client)
    res = await survey_answer(client, sid, digits="3", query="q=species")  # Goat
    assert_twiml(res, "How many animals are affected")
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import IVRSurvey, IVRSurveyResponse
    async with AsyncSessionLocal() as sdb:
        survey = (await sdb.execute(select(IVRSurvey).where(IVRSurvey.call_session_id == (await sdb.execute(
            select(__import__("backend.models", fromlist=["CallSession"]).CallSession.id)
            .where(__import__("backend.models", fromlist=["CallSession"]).CallSession.provider_call_id == sid)
        )).scalars().first()))).scalars().first()
        rows = (await sdb.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
        assert [(r.question, r.normalized_answer) for r in rows] == [("species", "Goat")]
        assert survey.current_question == "affected_count"


async def test_duplicate_survey_answer_does_not_duplicate_rows(client):
    sid, _ = await start_survey(client)
    await survey_answer(client, sid, digits="1", query="q=species")
    # replay of the same webhook (same digit, stale q) — current question already advanced,
    # but duplicate recording for the SAME question must be impossible (unique constraint).
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import IVRSurvey, IVRSurveyResponse, CallSession
    async with AsyncSessionLocal() as sdb:
        cs = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        survey = (await sdb.execute(select(IVRSurvey).where(IVRSurvey.call_session_id == cs.id))).scalars().first()
        n_before = (await sdb.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
        assert len(n_before) == 1
        # re-record same question (simulates a webhook replay at the storage level)
        from backend.services.ivr.survey_engine import SurveyEngine
        await SurveyEngine.record_answer(sdb, survey, "species", "1", "Cattle")
        rows = (await sdb.execute(select(IVRSurveyResponse).where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
        assert len(rows) == 1  # no duplicate row created
        await sdb.rollback()


# ------------------------------------------------------------------------------------------
# Full survey answers helper (valid sequence)
# ------------------------------------------------------------------------------------------
async def answer_full_survey(client, sid, *, location_speech=None):
    """species=Cattle, affected=4, symptoms=1+2, duration=1-2 days, deaths=0,
    vaccination=unknown(3), location speech/registered, confirm=1."""
    out = []
    out.append(await survey_answer(client, sid, digits="1", query="q=species"))          # Cattle
    out.append(await survey_answer(client, sid, digits="4", query="q=affected_count"))   # 4 animals
    out.append(await survey_answer(client, sid, digits="12", query="q=symptoms"))        # Fever + Loss of appetite
    out.append(await survey_answer(client, sid, digits="2", query="q=duration"))         # 1-2 days
    out.append(await survey_answer(client, sid, digits="0", query="q=deaths"))           # 0 dead
    out.append(await survey_answer(client, sid, digits="3", query="q=vaccination"))      # don't know
    if location_speech:
        out.append(await survey_answer(client, sid, speech=location_speech, query="q=location"))
    else:
        out.append(await survey_answer(client, sid, digits="1", query="q=location"))     # registered/unknown
    out.append(await survey_answer(client, sid, digits="1", query="q=confirm"))          # submit
    return out


# ------------------------------------------------------------------------------------------
# 8 + 9 + 14 + 15: report creation, triage integration, callback, completion (integration)
# ------------------------------------------------------------------------------------------
async def test_integration_inbound_language_survey_report_triage_callback(client):
    # ---- INBOUND ----
    sid, _ = await start_survey(client, caller=REGISTERED_FARMER_FROM)
    # NOTE: registered farmer in Pune -> an eligible vet exists -> <Dial> comes first (PATH A attempt)
    # We simulate the vet not answering (no-answer) which must fall back to the survey (PATH B).
    res = await post_twiml(client, "/api/v1/telephony/ivr",
                           {"CallSid": sid, "DialCallStatus": "no-answer"}, query="step=vet_dial")
    assert_twiml(res, "What animal is affected")

    # ---- SURVEY ----
    responses = await answer_full_survey(client, sid)
    final = responses[-1]
    body = assert_twiml(final)
    assert "report number" in body.lower()
    assert "goodbye" in body.lower()

    # ---- REPORT + TRIAGE (existing pipeline) ----
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession, CallbackRequest, DiseaseReport, IVRSurvey, VeterinaryCase, WorkflowEvent

    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session is not None and session.status == "CALLBACK_REQUESTED"
        assert session.language == "en"
        assert session.disease_report_id is not None
        assert session.ivr_survey_id is not None

        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert report is not None
        assert report.source == "IVR"                       # existing source enum
        assert report.species == "Cattle"
        assert report.number_affected == 4
        assert report.number_dead == 0
        assert report.symptoms == ["Fever", "Loss of appetite"]
        assert report.village and report.district           # resolved from farmer profile
        # existing triage ran (registered farmer -> Pune -> case offered to DEMO-VET)
        assert report.status in ("TRIAGED", "ASSIGNED")
        assert report.triage_risk_level == "HIGH"           # cluster >= 3 animals
        assert report.triage_urgency == "URGENT"
        assert report.triage_rule_version

        survey = await sdb.get(IVRSurvey, session.ivr_survey_id)
        assert survey.status == "COMPLETED" and survey.completed_at is not None
        assert survey.disease_report_id == report.id

        # existing VeterinaryCase + dispatch offer created by report_service
        cases = (await sdb.execute(select(VeterinaryCase).where(VeterinaryCase.report_id == report.id))).scalars().all()
        assert len(cases) == 1
        assert cases[0].status == "ASSIGNED"
        assert cases[0].assigned_vet_id == "DEMO-VET-001"

        # workflow events recorded by existing workflow service
        evs = (await sdb.execute(select(WorkflowEvent).where(WorkflowEvent.entity_id == report.id))).scalars().all()
        assert {e.to_status for e in evs} >= {"SUBMITTED", "TRIAGED", "ASSIGNED"}

        # CALLBACK (priority = existing triage severity)
        cb = (await sdb.execute(select(CallbackRequest).where(CallbackRequest.call_session_id == session.id))).scalars().first()
        assert cb is not None
        assert cb.priority == "HIGH"
        assert cb.status == "PENDING"
        assert cb.disease_report_id == report.id
        assert cb.species == "Cattle"
        report_id = report.id
        cb_id = cb.id
        call_id = session.id

    # ---- DASHBOARD: vet sees report + callback ----------------------------------------
    vh = await auth_headers(client, "veterinarian")
    cb_list = await client.get("/api/v1/callbacks", headers=vh)
    assert cb_list.status_code == 200, cb_list.text
    row = next((c for c in cb_list.json() if c["id"] == cb_id), None)
    assert row is not None
    assert row["priority"] == "HIGH" and row["status"] == "PENDING"
    assert row["species"] == "Cattle" and row["village"] and row["symptoms"]
    # PII: vet has PII_VIEW -> full phone; call row lists masked for others
    assert row["callerPhone"] and "*" not in row["callerPhone"]

    reports_list = await client.get("/api/v1/reports", headers=vh)
    assert any(r["id"] == report_id for r in reports_list.json())

    # ---- CALLBACK ACTIONS ----------------------------------------------------------------
    acc = await client.post(f"/api/v1/callbacks/{cb_id}/accept", headers=vh)
    assert acc.status_code == 200, acc.text
    assert acc.json()["status"] == "ACCEPTED"
    assert acc.json()["assignedVeterinarian"] is not None

    cc = await client.post(f"/api/v1/callbacks/{cb_id}/create-case", headers=vh)
    assert cc.status_code == 200, cc.text
    assert cc.json()["caseNumber"]

    done = await client.post(f"/api/v1/callbacks/{cb_id}/complete", json={"notes": "spoke to farmer"},
                             headers=vh)
    assert done.status_code == 200 and done.json()["status"] == "COMPLETED"

    # ---- CALL COMPLETION (provider status callback) ---------------------------------------
    st_params = {"CallSid": sid, "CallStatus": "completed", "CallDuration": "180"}
    res = await post_twiml(client, "/api/v1/telephony/status", st_params)
    assert res.status_code == 200 and res.text.strip().startswith("<Response")
    from backend.services.telephony import call_router
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = await sdb.get(CallSession, call_id)
        assert session.status == call_router.COMPLETED
        assert session.ended_at is not None

    # ---- CALLS DASHBOARD -------------------------------------------------------------------
    calls_list = await client.get("/api/v1/telephony/calls", headers=vh)
    assert calls_list.status_code == 200
    row = next((c for c in calls_list.json() if c["id"] == call_id), None)
    assert row is not None
    detail = await client.get(f"/api/v1/telephony/calls/{call_id}", headers=vh)
    assert detail.status_code == 200
    d = detail.json()
    assert d["reportId"] == report_id and d["triageRiskLevel"] == "HIGH"
    assert d["callback"]["id"] == cb_id
    assert any(a["question"] == "species" and a["normalized"] == "Cattle" for a in d["answers"])


# ------------------------------------------------------------------------------------------
# 10-13: veterinarian availability paths
# ------------------------------------------------------------------------------------------
async def test_vet_available_dials_eligible_vet(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": REGISTERED_FARMER_FROM})
    res = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
    body = assert_twiml(res, "<Dial")
    assert "9000000002" in body  # DEMO-VET-001 phone (bridged via Twilio <Dial>)
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.status == "VET_DIALING"
        assert session.veterinarian_id == "DEMO-VET-001"
        assert len(session.vet_attempts) == 1 and session.vet_attempts[0]["result"] == "dialing"


async def test_vet_connected_bridges_and_says_goodbye(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": REGISTERED_FARMER_FROM})
    await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
    res = await post_twiml(client, "/api/v1/telephony/ivr",
                           {"CallSid": sid, "DialCallStatus": "completed", "DialCallDuration": "120"},
                           query="step=vet_dial")
    assert_twiml(res, "Goodbye")
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.status == "BRIDGED"
        assert session.veterinarian_id == "DEMO-VET-001"
        assert session.vet_attempts[-1]["result"] == "completed"


async def test_vet_busy_falls_back_to_survey(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": REGISTERED_FARMER_FROM})
    await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
    res = await post_twiml(client, "/api/v1/telephony/ivr",
                           {"CallSid": sid, "DialCallStatus": "busy"}, query="step=vet_dial")
    assert_twiml(res, "What animal is affected")
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession, IVRSurvey
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.status == "SURVEY"
        assert session.vet_attempts[-1]["result"] == "busy"
        survey = await sdb.get(IVRSurvey, session.ivr_survey_id)
        assert survey is not None and survey.status == "IN_PROGRESS"


async def test_multiple_vet_attempts_respect_max_limit(client, monkeypatch):
    # add a second eligible vet in Pune
    from backend.database import AsyncSessionLocal
    from backend.models import User, UserRole, VeterinarianProfile
    from backend.security import hash_password
    async with AsyncSessionLocal() as sdb:
        sdb.add(User(id="TEST-VET-002", email=f"vet2{uuid.uuid4().hex[:6]}@example.in", phone="9000000099",
                     hashed_password=hash_password("Str0ng!Passw0rd"), role=UserRole.VETERINARIAN.value,
                     full_name="Second Test Vet", district="Pune", is_active=True, is_verified=True,
                     license_number="TEST-L2"))
        await sdb.flush()
        sdb.add(VeterinarianProfile(user_id="TEST-VET-002", availability_status="AVAILABLE", service_radius_km=80))
        await sdb.commit()

    from backend.config import settings
    monkeypatch.setattr(settings, "IVR_MAX_VET_ATTEMPTS", 1)  # only one attempt allowed

    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": REGISTERED_FARMER_FROM})
    res1 = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
    assert_twiml(res1, "<Dial")
    # first vet no-answer; limit reached -> straight to survey (no second dial)
    res2 = await post_twiml(client, "/api/v1/telephony/ivr",
                            {"CallSid": sid, "DialCallStatus": "no-answer"}, query="step=vet_dial")
    body = assert_twiml(res2, "What animal is affected")
    assert "<Dial" not in body

    from sqlalchemy import select
    from backend.database import AsyncSessionLocal as ASL
    from backend.models import CallSession
    async with ASL() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert len(session.vet_attempts) == 1  # IVR_MAX_VET_ATTEMPTS=1 honoured

    # raise the limit again -> second candidate gets dialed on a fresh call
    monkeypatch.setattr(settings, "IVR_MAX_VET_ATTEMPTS", 3)
    sid2 = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid2, "From": REGISTERED_FARMER_FROM})
    r = await post_twiml(client, "/api/v1/telephony/ivr", {"CallSid": sid2, "Digits": "1"})
    assert_twiml(r, "<Dial")
    r2 = await post_twiml(client, "/api/v1/telephony/ivr",
                          {"CallSid": sid2, "DialCallStatus": "no-answer"}, query="step=vet_dial")
    # either a second Dial (another candidate) or the survey (all candidates exhausted)
    assert "<Dial" in r2.text or "What animal is affected" in r2.text
    async with ASL() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid2))).scalars().first()
        attempted = [a["vet_id"] for a in session.vet_attempts]
        assert len(attempted) == len(set(attempted))  # never re-dial the same vet


# ------------------------------------------------------------------------------------------
# 16: provider failure / status handling
# ------------------------------------------------------------------------------------------
async def test_status_callback_failure_marks_call_failed(client):
    sid = f"CA{uuid.uuid4().hex[:14]}"
    await post_twiml(client, "/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
    res = await post_twiml(client, "/api/v1/telephony/status",
                           {"CallSid": sid, "CallStatus": "failed"})
    assert res.status_code == 200 and res.text.strip().startswith("<Response")
    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.status == "FAILED"
        assert session.last_error == "provider:failed"
        assert session.ended_at is not None
    # duplicate status webhook is idempotent
    res2 = await post_twiml(client, "/api/v1/telephony/status",
                            {"CallSid": sid, "CallStatus": "failed"})
    assert res2.status_code == 200
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.status == "FAILED"


async def test_unknown_call_sid_returns_404(client):
    res = await post_twiml(client, "/api/v1/telephony/status",
                           {"CallSid": "CAnotexist", "CallStatus": "completed"})
    assert res.status_code == 404


# ------------------------------------------------------------------------------------------
# 17: unauthorized dashboard access
# ------------------------------------------------------------------------------------------
async def test_unauthorized_dashboard_access(client):
    # anonymous
    assert (await client.get("/api/v1/telephony/calls")).status_code == 401
    assert (await client.get("/api/v1/telephony/calls/anything")).status_code == 401
    assert (await client.get("/api/v1/callbacks")).status_code == 401
    # lab technician: no REPORT_READ / CASE_READ
    lh = await auth_headers(client, "lab")
    assert (await client.get("/api/v1/telephony/calls", headers=lh)).status_code == 403
    assert (await client.get("/api/v1/callbacks", headers=lh)).status_code == 403
    # farmer cannot accept callbacks (needs CASE_UPDATE)
    fh = await auth_headers(client, "farmer")
    assert (await client.post("/api/v1/callbacks/CBK-x/accept", headers=fh)).status_code in (401, 403, 404)
    # farmer sees only own calls
    calls = await client.get("/api/v1/telephony/calls", headers=fh)
    assert calls.status_code == 200
    assert all(c["farmerId"] == "DEMO-FARMER-001" for c in calls.json())
    # farmer cannot read someone else's transcript
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    from sqlalchemy import select
    async with AsyncSessionLocal() as sdb:
        other = (await sdb.execute(select(CallSession).where(CallSession.farmer_id.is_(None)))).scalars().first()
    if other:
        assert (await client.get(f"/api/v1/telephony/calls/{other.id}/transcript", headers=fh)).status_code == 403


async def test_farmer_phone_masked_without_pii_permission(client):
    """A viewer without PII_VIEW sees only the masked phone."""
    from backend.security import mask_phone, phone_for_viewer, has_permission, Permission
    from backend.models import User
    viewer = User(id="x", email="x@y.z", hashed_password="h", role="FARMER", full_name="X")
    owner = User(id="y", email="a@b.c", hashed_password="h", role="FARMER", full_name="Y")
    assert has_permission(viewer, Permission.PII_VIEW) is False
    assert phone_for_viewer(viewer, "+919000000001", owner_id=owner.id) == mask_phone("+919000000001")
    assert phone_for_viewer(owner, "+919000000001", owner_id=owner.id) == "+919000000001"


# ------------------------------------------------------------------------------------------
# 18: MockTelephonyProvider complete flow (webhooks signed with shared-secret mock)
# ------------------------------------------------------------------------------------------
async def test_mock_provider_complete_flow(client, monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "mock")
    sid = f"MOCK{uuid.uuid4().hex[:14]}"

    # mock with no shared secret: unsigned accepted (signature path still exercised by twilio tests)
    res = await client.post("/api/v1/telephony/inbound", data={"CallSid": sid, "From": UNKNOWN_FROM})
    assert_twiml(res, WELCOME)

    res = await client.post("/api/v1/telephony/ivr", data={"CallSid": sid, "Digits": "1"})
    assert_twiml(res, "What animal is affected")

    # mark session simulated via mock provider semantics + run the full survey
    async def mock_post(path, params, query=""):
        return await client.post(path + (f"?{query}" if query else ""), data={"CallSid": sid, **params})

    for path, params, q in [
        ("/api/v1/telephony/survey", {"Digits": "1"}, "q=species"),
        ("/api/v1/telephony/survey", {"Digits": "4"}, "q=affected_count"),
        ("/api/v1/telephony/survey", {"Digits": "12"}, "q=symptoms"),
        ("/api/v1/telephony/survey", {"Digits": "2"}, "q=duration"),
        ("/api/v1/telephony/survey", {"Digits": "1"}, "q=deaths"),
        ("/api/v1/telephony/survey", {"Digits": "1"}, "q=vaccination"),
        ("/api/v1/telephony/survey", {"SpeechResult": "Wardha"}, "q=location"),
        ("/api/v1/telephony/survey", {"Digits": "1"}, "q=confirm"),
    ]:
        res = await mock_post(path, params, q)
        assert res.status_code == 200, res.text

    from sqlalchemy import select
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession, CallbackRequest, DiseaseReport
    async with AsyncSessionLocal() as sdb:
        session = (await sdb.execute(select(CallSession).where(CallSession.provider_call_id == sid))).scalars().first()
        assert session.provider == "mock"
        assert session.is_simulated is True            # clearly labelled as simulated
        assert session.disease_report_id is not None
        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert report.source == "IVR"
        assert report.village == "Wardha"              # speech answer stored
        cb = (await sdb.execute(select(CallbackRequest).where(CallbackRequest.call_session_id == session.id))).scalars().first()
        assert cb is not None and cb.is_simulated is True
        assert cb.priority in ("LOW", "MODERATE", "HIGH", "CRITICAL")


# ------------------------------------------------------------------------------------------
# DEMO_MODE simulation endpoint
# ------------------------------------------------------------------------------------------
async def test_demo_simulate_requires_auth_and_demo_mode(client, monkeypatch):
    from backend.config import settings
    # anonymous
    res = await client.post("/api/v1/telephony/demo/simulate", json={})
    assert res.status_code == 401
    # farmer role not allowed
    fh = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/telephony/demo/simulate", json={}, headers=fh)
    assert res.status_code == 403
    # vet allowed when DEMO_MODE=true
    vh = await auth_headers(client, "veterinarian")
    res = await client.post("/api/v1/telephony/demo/simulate",
                            json={"language": "en", "scenario": "vet_unavailable",
                                  "district": "Pune",
                                  "answers": {"species": "2", "affected_count": "6", "symptoms": "1",
                                              "duration": "3", "deaths": "0", "vaccination": "1",
                                              "location": "1"}},
                            headers=vh)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["label"] == "DEMO / SIMULATED"
    assert body["provider"] == "mock"
    assert body["reportId"] and body["callbackId"]
    assert body["callSession"]["isSimulated"] is True
    # disabled when DEMO_MODE=false
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    res = await client.post("/api/v1/telephony/demo/simulate", json={}, headers=vh)
    assert res.status_code == 403


async def test_demo_simulate_vet_available_scenario(client):
    vh = await auth_headers(client, "veterinarian")
    res = await client.post("/api/v1/telephony/demo/simulate",
                            json={"language": "en", "scenario": "vet_available", "district": "Pune"},
                            headers=vh)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["scenario"] == "vet_available"
    assert "bridged" in body["steps"]
    assert body["transcriptAvailable"] is True


# ------------------------------------------------------------------------------------------
# IVR disable switch (safe off)
# ------------------------------------------------------------------------------------------
async def test_ivr_disabled_returns_polite_twiml(client, monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "IVR_ENABLED", False)
    params = {"CallSid": f"CA{uuid.uuid4().hex[:14]}", "From": UNKNOWN_FROM}
    res = await post_twiml(client, "/api/v1/telephony/inbound", params)
    body = assert_twiml(res, "currently unavailable")
    assert "<Gather" not in body  # no interactive flow when disabled
    # no session created
    from sqlalchemy import select, func
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        n = (await sdb.execute(select(func.count()).where(CallSession.provider_call_id == params["CallSid"]))).scalar()
    assert n == 0


# ------------------------------------------------------------------------------------------
# Recording + transcript: RBAC and audit
# ------------------------------------------------------------------------------------------
async def test_recording_and_transcript_rbac_and_audit(client, monkeypatch):
    from backend.config import settings
    from backend.database import AsyncSessionLocal
    from backend.models import CallSession, CallTranscript
    call_id = f"CAL-{uuid.uuid4().hex[:10].upper()}"
    async with AsyncSessionLocal() as sdb:
        sdb.add(CallSession(id=call_id, provider="mock", provider_call_id=f"MOCKRA{uuid.uuid4().hex[:10]}",
                            caller_phone="+919876543210", district="Pune", status="COMPLETED",
                            recording_status="COMPLETED", recording_url="https://api.twilio.com/recordings/RE-test",
                            transcription_status="COMPLETED", is_simulated=True))
        sdb.add(CallTranscript(id=f"TRN-{uuid.uuid4().hex[:10]}", call_session_id=call_id,
                               speaker="MIXED", text="fever since two days in 4 cattle", language="en", source="STT"))
        await sdb.commit()

    # anonymous -> 401
    assert (await client.get(f"/api/v1/telephony/calls/{call_id}/recording")).status_code == 401
    # farmer not owner -> 403 (call has no farmer owner and district-scoped farmer role)
    fh = await auth_headers(client, "farmer")
    assert (await client.get(f"/api/v1/telephony/calls/{call_id}/recording", headers=fh)).status_code == 403

    # vet in district Pune: transcript works; recording downloads through the MOCK provider
    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "mock")
    vh = await auth_headers(client, "veterinarian")
    tr = await client.get(f"/api/v1/telephony/calls/{call_id}/transcript", headers=vh)
    assert tr.status_code == 200, tr.text
    assert tr.json()["segments"][0]["text"] == "fever since two days in 4 cattle"
    rec = await client.get(f"/api/v1/telephony/calls/{call_id}/recording", headers=vh)
    assert rec.status_code == 200, rec.text
    assert rec.headers["content-type"].startswith("audio/")
    assert rec.headers.get("cache-control") == "no-store"

    # both accesses audited
    from sqlalchemy import select
    from backend.models import AuditLog
    async with AsyncSessionLocal() as sdb:
        actions = (await sdb.execute(select(AuditLog.action).where(AuditLog.resource_id == call_id))).scalars().all()
    assert "RECORDING_ACCESSED" in actions
    assert "TRANSCRIPT_ACCESSED" in actions

    # recording missing -> 404
    call2 = f"CAL-{uuid.uuid4().hex[:10].upper()}"
    async with AsyncSessionLocal() as sdb:
        sdb.add(CallSession(id=call2, provider="mock", provider_call_id=f"MOCKRB{uuid.uuid4().hex[:10]}",
                            district="Pune", status="COMPLETED", recording_status="NONE"))
        await sdb.commit()
    assert (await client.get(f"/api/v1/telephony/calls/{call2}/recording", headers=vh)).status_code == 404


# ------------------------------------------------------------------------------------------
# Voice helpers: extraction never fabricates
# ------------------------------------------------------------------------------------------
async def test_transcript_extraction_and_summary_do_not_fabricate():
    from backend.services.voice import extract_fields, template_summary
    # nothing said -> all null
    empty = extract_fields(None)
    assert all(v is None for v in empty.values())
    # only what is present
    f = extract_fields("4 cattle with fever since 2 days, 1 dead, village Rampur, not vaccinated")
    assert f["species"] == "Cattle"
    assert f["affected_count"] == 4
    assert f["deaths"] == 1
    assert "Fever" in (f["symptoms"] or [])
    assert f["vaccination_status"] is False
    assert f["location"] == "Rampur"
    assert f["temperature"] is None          # never said -> not invented
    summary = template_summary(f)
    assert "Species: Cattle" in summary
    assert "Veterinary assessment required" in summary
    assert "not a diagnosis" in summary.lower()
    # missing fields shown as Unknown, never guessed
    assert "Temperature: Unknown" in summary


# ------------------------------------------------------------------------------------------
# Call state machine unit checks
# ------------------------------------------------------------------------------------------
async def test_call_state_machine_rules():
    from backend.services.telephony import call_router as cr

    class S:
        status = "INBOUND"
        id = "CAL-X"
    s = S()
    assert cr.apply_transition(s, "COMPLETED", reason="dup") is True
    assert s.status == "COMPLETED"
    # terminal state cannot regress
    assert cr.apply_transition(s, "SURVEY", reason="late webhook") is False
    assert s.status == "COMPLETED"
    # illegal jump ignored
    s2 = S()
    assert cr.apply_transition(s2, "TRIAGED", reason="illegal") is False
    assert s2.status == "INBOUND"
    assert cr.can_transition("SURVEY", "REPORT_CREATED")
    assert not cr.can_transition("REPORT_CREATED", "SURVEY")
