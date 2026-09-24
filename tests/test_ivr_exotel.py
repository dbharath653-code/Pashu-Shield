"""Exotel IVR test-suite (spec §26).

Covers: 1 incoming call, 2 unknown caller, 3 registered caller, 4 menu selection,
5 invalid DTMF, 6 disease report, 7 emergency report, 8 veterinarian request,
9 case status, 10 duplicate webhook, 11 malformed webhook, 12 missing caller number,
13 triage failure, 14 database failure, 15 notification failure,
16 authentication/signature failure, 17 unknown/expired session,
plus ExoML rendering + Exotel parameter parsing unit tests and the required
end-to-end integration test:

    Exotel webhook -> FastAPI -> DiseaseReport -> triage -> VeterinaryCase -> callback

No test places a real call: every request is a mocked Exotel webhook POST carrying the
shared webhook secret, exactly as Exotel would send it.
"""
import os
import uuid

import pytest

from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio

SECRET = os.environ["EXOTEL_WEBHOOK_SECRET"]
EXOPHONE = os.environ["EXOTEL_PHONE_NUMBER"]
WELCOME = "Welcome to Pashu Shield livestock health helpline."

# Demo farmer phone (registered) -> identifies DEMO-FARMER-001, district Pune
REGISTERED_FARMER_FROM = "+919000000001"
UNKNOWN_FROM = "+919876543210"
DEMO_VET_PHONE = "9000000002"


def call_sid() -> str:
    """Exotel call ids are alpha-numeric (e.g. 80bfbec2d78bbbf10fb851f4fa165211)."""
    return uuid.uuid4().hex


async def post_exotel(client, path: str, params: dict, *, query: str = "", secret=SECRET,
                      send_secret: bool = True, headers: dict = None):
    """POST a webhook the way Exotel does: urlencoded body + the shared secret as ``?t=``."""
    url = f"/api/v1/ivr/{path}"
    qs = [p for p in (query, f"t={secret}" if (send_secret and secret) else "") if p]
    if qs:
        url += "?" + "&".join(qs)
    return await client.post(url, data=params, headers=headers or {})


def assert_exoml(res, *needles: str) -> str:
    assert res.status_code == 200, res.text
    assert "xml" in res.headers.get("content-type", ""), res.headers
    body = res.text
    assert body.startswith('<?xml version="1.0" encoding="UTF-8"?>'), body[:120]
    assert "<Response>" in body[:200], body[:200]
    for n in needles:
        assert n in body, f"missing {n!r} in {body[:900]}"
    return body


def session_url(res, step_marker: str) -> bool:
    """True when the document contains an action URL for the given ``step=``."""
    return f"step={step_marker}" in res.text


async def inbound(client, caller=UNKNOWN_FROM, sid=None) -> str:
    sid = sid or call_sid()
    res = await post_exotel(client, "incoming", {"CallSid": sid, "From": caller, "To": EXOPHONE,
                                                 "Direction": "incoming"})
    assert_exoml(res, WELCOME, "<Gather")
    return sid


async def choose_language(client, sid, digit="1"):
    return await post_exotel(client, "input", {"CallSid": sid, "digits": digit}, query="step=language")


async def choose_menu(client, sid, digit):
    return await post_exotel(client, "input", {"CallSid": sid, "digits": digit}, query="step=menu")


async def survey_answer(client, sid, digits=None, query=""):
    params = {"CallSid": sid}
    if digits is not None:
        params["digits"] = digits
    return await post_exotel(client, "input", params, query=query or "step=survey")


async def answer_full_survey(client, sid, *, species="1", affected="4", symptoms="12",
                             duration="2", deaths="0", vaccination="3", location="1"):
    """Cattle, 4 affected, Fever + Loss of appetite, 1-2 days, 0 dead, vaccination unknown,
    registered village, confirm."""
    out = [await survey_answer(client, sid, species, "step=survey&q=species")]
    out.append(await survey_answer(client, sid, affected, "step=survey&q=affected_count"))
    out.append(await survey_answer(client, sid, symptoms, "step=survey&q=symptoms"))
    out.append(await survey_answer(client, sid, duration, "step=survey&q=duration"))
    out.append(await survey_answer(client, sid, deaths, "step=survey&q=deaths"))
    out.append(await survey_answer(client, sid, vaccination, "step=survey&q=vaccination"))
    out.append(await survey_answer(client, sid, location, "step=survey&q=location"))
    out.append(await survey_answer(client, sid, "1", "step=survey&q=confirm"))
    return out


async def vet_phone(vet_id: str) -> str:
    from backend.database import AsyncSessionLocal
    from backend.models import User
    async with AsyncSessionLocal() as sdb:
        return (await sdb.get(User, vet_id)).phone


async def get_session(sid):
    from sqlalchemy import select

    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        return (await sdb.execute(select(CallSession)
                                  .where(CallSession.provider_call_id == sid))).scalars().first()


async def start_report_flow(client, caller=UNKNOWN_FROM):
    """inbound -> English -> menu 1 (report sick animal) -> first survey question."""
    sid = await inbound(client, caller)
    res = await choose_language(client, sid)
    assert_exoml(res, "Press 1 to report a sick animal")
    res = await choose_menu(client, sid, "1")
    assert_exoml(res, "What animal is affected")
    return sid


# ==========================================================================================
# 1) incoming call
# ==========================================================================================
async def test_incoming_call_returns_exoml_welcome_and_creates_session(client):
    sid = await inbound(client)
    session = await get_session(sid)
    assert session is not None
    assert session.provider == "exotel"
    assert session.provider_call_id == sid
    assert session.direction == "INBOUND"
    assert session.is_simulated is False
    assert session.status == "IDENTIFIED"
    assert session.caller_phone == "+919876543210"
    assert session.to_phone == EXOPHONE


async def test_ivr_disabled_returns_polite_exoml(client, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "IVR_ENABLED", False)
    sid = call_sid()
    res = await post_exotel(client, "incoming", {"CallSid": sid, "From": UNKNOWN_FROM})
    body = assert_exoml(res, "currently unavailable", "<Hangup")
    assert "<Gather" not in body


# ==========================================================================================
# 2 + 3) caller identification
# ==========================================================================================
async def test_unknown_caller_is_not_given_a_location(client):
    sid = await inbound(client, UNKNOWN_FROM)
    session = await get_session(sid)
    assert session.farmer_id is None
    # No fabricated Pune/Shirur: an unknown caller has no district at all.
    assert session.district is None


async def test_registered_caller_is_identified_by_phone(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    session = await get_session(sid)
    assert session.farmer_id == "DEMO-FARMER-001"
    assert session.district == "Pune"


async def test_missing_caller_number_is_accepted_and_stays_unknown(client):
    sid = call_sid()
    res = await post_exotel(client, "incoming", {"CallSid": sid, "To": EXOPHONE})
    assert_exoml(res, WELCOME)
    session = await get_session(sid)
    assert session.caller_phone is None
    assert session.farmer_id is None
    assert session.district is None
    # The survey must then ask for the location instead of assuming one.
    await choose_language(client, sid)
    await choose_menu(client, sid, "1")
    for q, digits in (("species", "1"), ("affected_count", "2"), ("symptoms", "1"),
                      ("duration", "2"), ("deaths", "0"), ("vaccination", "3")):
        await survey_answer(client, sid, digits, f"step=survey&q={q}")
    res = await survey_answer(client, sid, "1", "step=survey&q=location")
    # "1" = registered village, but there is no registered caller -> location stays Unknown.
    assert_exoml(res, "Please confirm")
    final = await survey_answer(client, sid, "1", "step=survey&q=confirm")
    assert_exoml(final, "report number")
    from backend.database import AsyncSessionLocal
    from backend.models import DiseaseReport
    session = await get_session(sid)
    async with AsyncSessionLocal() as sdb:
        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert report.district == "Unknown"
        assert report.village == "Unknown"
        assert report.location_status == "LOCATION_UNAVAILABLE"


# ==========================================================================================
# 4) main menu
# ==========================================================================================
async def test_language_then_main_menu(client):
    sid = await inbound(client)
    res = await choose_language(client, sid, "2")  # Hindi
    body = assert_exoml(res, "बीमार पशु की रिपोर्ट के लिए 1")
    assert 'language="hi"' in body
    session = await get_session(sid)
    assert session.language == "hi"
    assert session.status == "LANGUAGE_SELECTED"


async def test_invalid_language_digit_reasks(client):
    sid = await inbound(client)
    res = await choose_language(client, sid, "9")
    assert_exoml(res, "not a valid option", "Press 1 for English")
    session = await get_session(sid)
    assert session.language is None


async def test_invalid_menu_digit_reasks_menu(client):
    sid = await inbound(client)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "7")
    assert_exoml(res, "not a valid option", "Press 1 to report a sick animal")
    session = await get_session(sid)
    assert session.ivr_menu_option is None


async def test_menu_selection_is_recorded(client):
    for digit, expected in (("1", "1"), ("2", "2"), ("3", "3"), ("0", "0")):
        sid = await inbound(client, REGISTERED_FARMER_FROM)
        await choose_language(client, sid)
        await choose_menu(client, sid, digit)
        session = await get_session(sid)
        assert session.ivr_menu_option == expected
        # The state machine advances straight past MENU_SELECTED into the chosen branch.
        assert session.status in {"SURVEY", "VET_DIALING", "CASE_STATUS"}


# ==========================================================================================
# 5) invalid DTMF inside the survey
# ==========================================================================================
async def test_invalid_survey_dtmf_reasks_same_question(client):
    sid = await start_report_flow(client)
    res = await survey_answer(client, sid, "9", "step=survey&q=species")
    body = assert_exoml(res, "What animal is affected")
    assert "not a valid option" in body


async def test_survey_answers_persist_and_advance(client):
    sid = await start_report_flow(client)
    res = await survey_answer(client, sid, "3", "step=survey&q=species")  # Goat
    assert_exoml(res, "How many animals are affected")
    from sqlalchemy import select

    from backend.database import AsyncSessionLocal
    from backend.models import IVRSurvey, IVRSurveyResponse
    session = await get_session(sid)
    async with AsyncSessionLocal() as sdb:
        survey = await sdb.get(IVRSurvey, session.ivr_survey_id)
        rows = (await sdb.execute(select(IVRSurveyResponse)
                                  .where(IVRSurveyResponse.survey_id == survey.id))).scalars().all()
        assert [(r.question, r.normalized_answer) for r in rows] == [("species", "Goat")]
        assert survey.current_question == "affected_count"


# ==========================================================================================
# 6) disease report -> existing pipeline (also the end-to-end integration test)
# ==========================================================================================
async def test_integration_exotel_webhook_to_report_triage_case_callback(client):
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    responses = await answer_full_survey(client, sid)
    body = assert_exoml(responses[-1])
    assert "report number" in body.lower()
    assert "Goodbye" in body

    from sqlalchemy import select

    from backend.database import AsyncSessionLocal
    from backend.models import (CallbackRequest, DiseaseReport, IVRSurvey, VeterinaryCase,
                                WorkflowEvent)
    session = await get_session(sid)
    assert session.status == "CALLBACK_REQUESTED"
    assert session.language == "en"
    assert session.ivr_menu_option == "1"
    assert session.is_emergency is False
    assert session.disease_report_id is not None

    async with AsyncSessionLocal() as sdb:
        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert report.source == "IVR"                    # reuses the existing source field
        assert report.species == "Cattle"
        assert report.number_affected == 4
        assert report.number_dead == 0
        assert report.symptoms == ["Fever", "Loss of appetite"]
        assert report.district == "Pune" and report.village == "Shirur"
        assert report.suspected_disease == "Unknown"     # a phone survey never diagnoses
        assert report.status in ("TRIAGED", "ASSIGNED")
        assert report.triage_risk_level == "HIGH"        # existing rule engine decided this
        assert report.triage_urgency == "URGENT"

        survey = await sdb.get(IVRSurvey, session.ivr_survey_id)
        assert survey.status == "COMPLETED" and survey.completed_at is not None

        cases = (await sdb.execute(select(VeterinaryCase)
                                   .where(VeterinaryCase.report_id == report.id))).scalars().all()
        assert len(cases) == 1                           # exactly one case, from report_service
        assert cases[0].status == "ASSIGNED"
        assert cases[0].assigned_vet_id == "DEMO-VET-001"

        events = (await sdb.execute(select(WorkflowEvent)
                                    .where(WorkflowEvent.entity_id == report.id))).scalars().all()
        assert events                                     # existing workflow audit trail

        cb = (await sdb.execute(select(CallbackRequest)
                                .where(CallbackRequest.call_session_id == session.id))).scalars().first()
        assert cb is not None and cb.priority == "HIGH"   # priority == triage severity
        assert cb.disease_report_id == report.id


async def test_report_number_is_announced_to_the_caller(client):
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    responses = await answer_full_survey(client, sid)
    body = assert_exoml(responses[-1])
    session = await get_session(sid)
    from backend.database import AsyncSessionLocal
    from backend.models import DiseaseReport
    async with AsyncSessionLocal() as sdb:
        report = await sdb.get(DiseaseReport, session.disease_report_id)
    assert report.report_number in body


async def test_location_option_2_keeps_location_unknown(client):
    """Keypad callers cannot type a village name; choosing "different place" must store
    UNKNOWN, never an assumed village."""
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    await answer_full_survey(client, sid, location="2")
    session = await get_session(sid)
    from backend.database import AsyncSessionLocal
    from backend.models import DiseaseReport
    async with AsyncSessionLocal() as sdb:
        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert report.village == "Unknown"
        assert report.location_status == "LOCATION_UNAVAILABLE"
        assert "different location" in (report.notes or "")


# ==========================================================================================
# 7) emergency (menu 0)
# ==========================================================================================
async def test_emergency_menu_marks_the_call_but_does_not_diagnose(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "0")
    body = assert_exoml(res, "emergency option", "What animal is affected")
    assert "diagnosis" in body.lower()  # the caller is told a vet still has to diagnose
    session = await get_session(sid)
    assert session.is_emergency is True
    assert session.ivr_menu_option == "0"

    await answer_full_survey(client, sid)
    session = await get_session(sid)
    from sqlalchemy import select

    from backend.database import AsyncSessionLocal
    from backend.models import CallbackRequest, DiseaseReport
    async with AsyncSessionLocal() as sdb:
        report = await sdb.get(DiseaseReport, session.disease_report_id)
        assert "EMERGENCY" in report.notes
        assert report.suspected_disease == "Unknown"
        cb = (await sdb.execute(select(CallbackRequest)
                                .where(CallbackRequest.call_session_id == session.id))).scalars().first()
        assert "EMERGENCY" in cb.notes
        assert cb.priority == report.triage_risk_level   # triage still decides priority


# ==========================================================================================
# 8) veterinarian request (menu 2) — existing dispatch engine, ExoML <Dial>
# ==========================================================================================
async def test_veterinarian_request_bridges_eligible_vet(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "2")
    body = assert_exoml(res, "<Dial", "Searching for an available veterinarian")
    assert "step=vet_dial" in body
    assert f'callerId="{EXOPHONE}"' in body            # our ExoPhone is presented
    session = await get_session(sid)
    assert session.status == "VET_DIALING"
    assert session.veterinarian_id is not None
    # The bridged number is the assigned veterinarian's own registered phone.
    assert f"<Number>{await vet_phone(session.veterinarian_id)}</Number>" in body
    assert session.vet_attempts[0]["result"] == "dialing"


async def test_veterinarian_answered_bridges_and_says_goodbye(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    await choose_menu(client, sid, "2")
    res = await post_exotel(client, "input",
                            {"CallSid": sid, "DialCallStatus": "completed", "DialCallDuration": "120"},
                            query="step=vet_dial")
    assert_exoml(res, "Goodbye", "<Hangup")
    session = await get_session(sid)
    assert session.status == "BRIDGED"
    assert session.vet_attempts[-1]["result"] == "completed"


async def test_veterinarian_busy_falls_back_to_report_survey(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    await choose_menu(client, sid, "2")
    res = await post_exotel(client, "input", {"CallSid": sid, "DialCallStatus": "busy"},
                            query="step=vet_dial")
    assert_exoml(res, "What animal is affected")
    session = await get_session(sid)
    assert session.status == "SURVEY"
    assert session.vet_attempts[-1]["result"] == "busy"


async def test_unknown_caller_vet_request_goes_to_survey(client):
    """No registered location => no provable jurisdiction => never dial a vet blindly."""
    sid = await inbound(client, UNKNOWN_FROM)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "2")
    body = assert_exoml(res, "What animal is affected")
    assert "<Dial" not in body


async def test_vet_attempts_never_repeat_the_same_vet(client, monkeypatch):
    from backend.config import settings
    from backend.database import AsyncSessionLocal
    from backend.models import User, UserRole, VeterinarianProfile
    from backend.security import hash_password

    async with AsyncSessionLocal() as sdb:
        sdb.add(User(id="TEST-VET-002", email=f"vet2{uuid.uuid4().hex[:6]}@example.in",
                     phone="9000000099", hashed_password=hash_password("Str0ng!Passw0rd"),
                     role=UserRole.VETERINARIAN.value, full_name="Second Test Vet",
                     district="Pune", is_active=True, is_verified=True, license_number="TEST-L2"))
        await sdb.flush()
        sdb.add(VeterinarianProfile(user_id="TEST-VET-002", availability_status="AVAILABLE",
                                    service_radius_km=80))
        await sdb.commit()

    monkeypatch.setattr(settings, "IVR_MAX_VET_ATTEMPTS", 1)
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    await choose_menu(client, sid, "2")
    res = await post_exotel(client, "input", {"CallSid": sid, "DialCallStatus": "no-answer"},
                            query="step=vet_dial")
    body = assert_exoml(res, "What animal is affected")
    assert "<Dial" not in body                      # limit reached -> survey, not another dial
    session = await get_session(sid)
    assert len(session.vet_attempts) == 1

    monkeypatch.setattr(settings, "IVR_MAX_VET_ATTEMPTS", 3)
    sid2 = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid2)
    await choose_menu(client, sid2, "2")
    await post_exotel(client, "input", {"CallSid": sid2, "DialCallStatus": "no-answer"},
                      query="step=vet_dial")
    session2 = await get_session(sid2)
    attempted = [a["vet_id"] for a in session2.vet_attempts]
    assert len(attempted) == len(set(attempted))


# ==========================================================================================
# 9) case status (menu 3)
# ==========================================================================================
async def test_case_status_refused_for_unverified_caller(client):
    sid = await inbound(client, UNKNOWN_FROM)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "3")
    body = assert_exoml(res, "could not match this number", "<Hangup")
    assert "case" not in body.lower().split("could not match")[0]  # nothing disclosed first
    session = await get_session(sid)
    assert session.status == "CASE_STATUS"


async def test_case_status_reported_for_registered_caller(client):
    # First create a case through the normal IVR report flow.
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    await answer_full_survey(client, sid)

    sid2 = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid2)
    res = await choose_menu(client, sid2, "3")
    body = assert_exoml(res, "most recent case", "<Hangup")
    from backend.database import AsyncSessionLocal
    from backend.models import VeterinaryCase
    async with AsyncSessionLocal() as sdb:
        from sqlalchemy import select
        case = (await sdb.execute(select(VeterinaryCase)
                                  .where(VeterinaryCase.farmer_id == "DEMO-FARMER-001")
                                  .order_by(VeterinaryCase.created_at.desc())
                                  .limit(1))).scalars().first()
    assert case is not None and case.case_number in body
    assert "not a confirmed diagnosis" in body


async def test_case_status_when_caller_has_no_records(client):
    from backend.database import AsyncSessionLocal
    from backend.models import User, UserRole
    from backend.security import hash_password

    phone = f"91{uuid.uuid4().int % 100000000:08d}"
    async with AsyncSessionLocal() as sdb:
        sdb.add(User(id=f"TEST-FARMER-{uuid.uuid4().hex[:6]}",
                     email=f"farmer{uuid.uuid4().hex[:6]}@example.in", phone=phone,
                     hashed_password=hash_password("Str0ng!Passw0rd"),
                     role=UserRole.FARMER.value, full_name="Test Farmer", district="Nashik",
                     is_active=True, is_verified=True))
        await sdb.commit()
    sid = await inbound(client, f"+91{phone}")
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "3")
    assert_exoml(res, "do not have any report or case recorded")


# ==========================================================================================
# 10) duplicate webhook (Exotel retries)
# ==========================================================================================
async def test_duplicate_inbound_webhook_is_idempotent(client):
    sid = call_sid()
    params = {"CallSid": sid, "From": UNKNOWN_FROM, "To": EXOPHONE}
    r1 = await post_exotel(client, "incoming", params)
    r2 = await post_exotel(client, "incoming", params)
    assert_exoml(r1, WELCOME)
    assert_exoml(r2, WELCOME)
    from sqlalchemy import func, select

    from backend.database import AsyncSessionLocal
    from backend.models import CallSession
    async with AsyncSessionLocal() as sdb:
        count = (await sdb.execute(select(func.count())
                                   .where(CallSession.provider_call_id == sid))).scalar()
    assert count == 1


async def test_duplicate_confirm_webhook_never_creates_a_second_report(client):
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    await answer_full_survey(client, sid)
    session = await get_session(sid)
    first_report = session.disease_report_id
    # Replay the confirmation webhook: the survey is COMPLETED, so nothing new is created.
    res = await survey_answer(client, sid, "1", "step=survey&q=confirm")
    assert_exoml(res, "Goodbye")
    session = await get_session(sid)
    assert session.disease_report_id == first_report
    from sqlalchemy import func, select

    from backend.database import AsyncSessionLocal
    from backend.models import CallbackRequest, DiseaseReport, IVRSurvey
    async with AsyncSessionLocal() as sdb:
        surveys = (await sdb.execute(select(func.count())
                                     .where(IVRSurvey.call_session_id == session.id))).scalar()
        callbacks = (await sdb.execute(select(func.count())
                                       .where(CallbackRequest.call_session_id == session.id))).scalar()
        ivr_reports = (await sdb.execute(select(func.count())
                                         .where(DiseaseReport.source == "IVR",
                                                DiseaseReport.notes.contains(session.id)))).scalar()
    assert ivr_reports == 1 and surveys == 1 and callbacks == 1


# ==========================================================================================
# 11) malformed webhook
# ==========================================================================================
async def test_missing_call_id_is_rejected(client):
    res = await post_exotel(client, "incoming", {"From": UNKNOWN_FROM})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "MISSING_CALL_ID"


async def test_malformed_json_body_is_rejected(client):
    res = await client.post(f"/api/v1/ivr/incoming?t={SECRET}",
                            content=b"{not json", headers={"Content-Type": "application/json"})
    assert res.status_code == 401     # a body we cannot parse is not trusted
    assert res.json()["error"]["code"] == "INVALID_WEBHOOK"


async def test_json_status_callback_is_accepted(client):
    """Exotel can send StatusCallback as application/json (StatusCallbackContentType)."""
    sid = await inbound(client)
    res = await client.post(f"/api/v1/ivr/status?t={SECRET}",
                            json={"CallSid": sid, "Status": "completed",
                                  "ConversationDuration": 180},
                            headers={"Content-Type": "application/json"})
    assert res.status_code == 200
    session = await get_session(sid)
    assert session.status == "COMPLETED" and session.ended_at is not None


# ==========================================================================================
# 16) authentication / signature failure
# ==========================================================================================
async def test_missing_webhook_secret_is_rejected(client):
    res = await post_exotel(client, "incoming", {"CallSid": call_sid(), "From": UNKNOWN_FROM},
                            send_secret=False)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_WEBHOOK"


async def test_wrong_webhook_secret_is_rejected(client):
    res = await post_exotel(client, "incoming", {"CallSid": call_sid(), "From": UNKNOWN_FROM},
                            secret="not-the-real-secret")
    assert res.status_code == 401


async def test_secret_header_is_accepted(client):
    sid = call_sid()
    res = await post_exotel(client, "incoming", {"CallSid": sid, "From": UNKNOWN_FROM},
                            send_secret=False, headers={"X-Exotel-Webhook-Secret": SECRET})
    assert_exoml(res, WELCOME)


async def test_validation_enabled_without_secret_fails_closed(client, monkeypatch):
    from backend.config import settings
    from backend.services.telephony import reset_provider
    from backend.services.telephony.base import WebhookVerificationError
    from backend.services.telephony.exotel_provider import ExotelProvider

    monkeypatch.setattr(settings, "EXOTEL_WEBHOOK_SECRET", "")
    reset_provider()
    try:
        with pytest.raises(WebhookVerificationError):
            ExotelProvider().validate_webhook(b"", {"CallSid": "x"}, "anything")
    finally:
        reset_provider()


async def test_call_id_verification_rejects_foreign_call_id(client, monkeypatch):
    from backend.config import settings
    from backend.services.telephony import reset_provider

    async def deny(self, call_id):
        return False

    from backend.services.telephony.exotel_provider import ExotelProvider
    monkeypatch.setattr(ExotelProvider, "verify_call_id", deny)
    monkeypatch.setattr(settings, "EXOTEL_VERIFY_CALL_SID", True)
    reset_provider()
    try:
        res = await post_exotel(client, "incoming", {"CallSid": call_sid(), "From": UNKNOWN_FROM})
        assert res.status_code == 401
    finally:
        reset_provider()


# ==========================================================================================
# 17) unknown / expired session
# ==========================================================================================
async def test_follow_up_for_unknown_call_id_returns_404(client):
    res = await post_exotel(client, "input", {"CallSid": call_sid(), "digits": "1"},
                            query="step=language")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "CALL_NOT_FOUND"


async def test_status_callback_for_unknown_call_id_returns_404(client):
    res = await post_exotel(client, "status", {"CallSid": call_sid(), "Status": "completed"})
    assert res.status_code == 404


# ==========================================================================================
# 13) triage failure
# ==========================================================================================
async def test_triage_failure_is_handled_and_the_caller_hears_a_message(client, monkeypatch):
    from backend.services.triage_service import TriageEngine

    def boom(*args, **kwargs):
        raise RuntimeError("triage engine exploded")

    monkeypatch.setattr(TriageEngine, "evaluate", staticmethod(boom))
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    responses = await answer_full_survey(client, sid)
    body = assert_exoml(responses[-1])          # 200 + a polite message, never a stack trace
    assert "unavailable" in body.lower()
    session = await get_session(sid)
    assert session.disease_report_id is None     # nothing half-written


# ==========================================================================================
# 14) database failure
# ==========================================================================================
async def test_database_failure_returns_a_polite_message(client, monkeypatch):
    import backend.routers.ivr as ivr_router

    class Broken:
        async def __aenter__(self):
            raise RuntimeError("database unavailable")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(ivr_router, "AsyncSessionLocal", Broken)
    res = await post_exotel(client, "incoming", {"CallSid": call_sid(), "From": UNKNOWN_FROM})
    assert res.status_code == 200                # the farmer hears something, not dead air
    body = assert_exoml(res, "<Hangup")
    assert "Traceback" not in body


# ==========================================================================================
# 15) notification failure
# ==========================================================================================
async def test_notification_failure_does_not_break_the_call(client, monkeypatch):
    from backend.services.notification_service import NotificationService

    async def boom(*args, **kwargs):
        raise RuntimeError("notification backend down")

    monkeypatch.setattr(NotificationService, "queue", staticmethod(boom))
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    await choose_language(client, sid)
    res = await choose_menu(client, sid, "2")
    body = assert_exoml(res, "<Dial")                  # the vet is still dialled
    session = await get_session(sid)
    assert session.status == "VET_DIALING"
    assert f"<Number>{await vet_phone(session.veterinarian_id)}</Number>" in body


# ==========================================================================================
# ExoML rendering + Exotel parameter parsing (unit level)
# ==========================================================================================
async def test_exoml_renders_exotel_verbs_only():
    from backend.services.telephony.exoml import render_exoml
    from backend.services.telephony.markup import VoiceDoc

    doc = (VoiceDoc()
           .say("Hello", language="mr")
           .gather("Press 1", "https://x.test/api/v1/ivr/input?step=menu&t=s",
                   language="en", num_digits=1, timeout=8)
           .dial("+919000000002", "https://x.test/api/v1/ivr/input?step=vet_dial",
                 timeout=20, caller_id="08047491899", record=True)
           .redirect("https://x.test/api/v1/ivr/input?step=survey")
           .hangup())
    xml = render_exoml(doc)
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert '<Say language="mr">Hello</Say>' in xml
    assert '<Gather action="https://x.test/api/v1/ivr/input?step=menu&amp;t=s" method="POST"' in xml
    assert 'numDigits="1"' in xml and 'finishOnKey="#"' in xml
    assert "<Number>+919000000002</Number>" in xml
    assert 'callerId="08047491899"' in xml and 'record="true"' in xml
    # ExoML <Redirect> carries the URL as element text, not an attribute.
    assert "<Redirect method=\"POST\">https://x.test/api/v1/ivr/input?step=survey</Redirect>" in xml
    assert "<Hangup></Hangup>" in xml
    # ExoML has no speech gather: nothing Twilio-only may leak into the document.
    for twilio_only in ("speechTimeout", 'input="dtmf speech"', "statusCallback", "record-from-answer"):
        assert twilio_only not in xml


async def test_exoml_speech_request_degrades_to_dtmf():
    from backend.services.telephony.exoml import render_exoml
    from backend.services.telephony.markup import VoiceDoc

    xml = render_exoml(VoiceDoc().gather("Say your village", "https://x.test/a", speech=True))
    assert "speech" not in xml.lower()


async def test_exotel_provider_parses_documented_parameters():
    from backend.services.telephony.exotel_provider import ExotelProvider

    p = ExotelProvider()
    assert p.get_call_id({"CallSid": " abc123 "}) == "abc123"
    assert p.get_caller_number({"From": "+919876543210"}) == "+919876543210"
    assert p.get_called_number({"To": "08047491899"}) == "08047491899"
    assert p.get_direction({"Direction": "incoming"}) == "incoming"
    # Exotel wraps the gathered digits in double quotes in several contexts.
    assert p.get_digits({"digits": '"13"'}) == "13"
    assert p.get_digits({"Digits": "4#"}) == "4"
    assert p.get_digits({}) == ""
    assert p.get_dial_result({"DialCallStatus": "No-Answer"}) == "no-answer"
    assert p.get_provider_status({"Status": "COMPLETED"}) == "completed"
    assert p.get_recording_url({"RecordingUrl": "https://recordings.exotel.com/x.mp3"})
    assert p.get_recording_url({"RecordingUrl": "http://insecure/x.mp3"}) is None
    assert p.markup_dialect == "exoml"
    assert p.supports_speech_input is False


async def test_exotel_recording_download_refuses_non_https():
    from backend.services.telephony.base import WebhookVerificationError
    from backend.services.telephony.exotel_provider import ExotelProvider

    with pytest.raises(WebhookVerificationError):
        await ExotelProvider().download_recording("http://recordings.exotel.com/x.mp3")


# ==========================================================================================
# StatusCallback + dashboard
# ==========================================================================================
async def test_status_callback_records_completion_and_recording(client):
    sid = await inbound(client, REGISTERED_FARMER_FROM)
    res = await post_exotel(client, "status",
                            {"CallSid": sid, "Status": "completed", "ConversationDuration": "200",
                             "RecordingUrl": "https://recordings.exotel.com/exotelrecordings/x.mp3",
                             "EventType": "terminal", "Direction": "inbound"})
    assert res.status_code == 200
    session = await get_session(sid)
    assert session.status == "COMPLETED"
    assert session.recording_status == "COMPLETED"
    assert session.recording_url.startswith("https://recordings.exotel.com/")
    assert session.recording_duration == 200


async def test_status_callback_failure_marks_call_failed(client):
    sid = await inbound(client, UNKNOWN_FROM)
    await post_exotel(client, "status", {"CallSid": sid, "Status": "no-answer"})
    session = await get_session(sid)
    assert session.status == "FAILED"
    assert session.last_error == "provider:no-answer"
    assert session.ended_at is not None


async def test_dashboard_lists_the_call_with_its_channel(client):
    sid = await start_report_flow(client, REGISTERED_FARMER_FROM)
    await answer_full_survey(client, sid)
    session = await get_session(sid)
    headers = await auth_headers(client, "veterinarian")
    res = await client.get("/api/v1/telephony/calls", headers=headers)
    assert res.status_code == 200, res.text
    row = next((c for c in res.json() if c["id"] == session.id), None)
    assert row is not None
    assert row["provider"] == "exotel"
    assert row["callSid"] == sid
    assert row["ivrMenuOption"] == "1"
    assert row["isEmergency"] is False
    assert row["reportId"] == session.disease_report_id


# ==========================================================================================
# Mock provider (DEMO_MODE) still runs the whole flow, clearly labelled
# ==========================================================================================
async def test_demo_simulation_is_labelled_and_creates_a_report(client, monkeypatch):
    from backend.config import settings
    from backend.services.telephony import reset_provider

    monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "mock")
    reset_provider()
    try:
        headers = await auth_headers(client, "veterinarian")
        res = await client.post("/api/v1/telephony/demo/simulate", json={"scenario": "vet_unavailable"},
                                headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["label"] == "DEMO / SIMULATED"
        assert data["callSession"]["provider"] == "mock"
        assert data["callSession"]["isSimulated"] is True
        # No hardcoded Pune/Shirur fallback: an unregistered simulated caller stays Unknown.
        assert data["callSession"]["district"] in (None, "Unknown")
        assert data["reportId"] and data["callbackId"]
    finally:
        monkeypatch.setattr(settings, "TELEPHONY_PROVIDER", "exotel")
        reset_provider()
