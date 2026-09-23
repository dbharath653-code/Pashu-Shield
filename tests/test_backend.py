"""End-to-end API tests (security, pipeline, offline sync, provenance)."""
import uuid

import pytest

from tests.conftest import DEMO_PASSWORD, auth_headers, login

pytestmark = pytest.mark.asyncio

REPORT = {"species": "Cattle", "number_affected": 3, "number_dead": 1, "symptoms": ["High Fever", "Blisters on gums", "Severe lameness"],
          "temperature": 105.0, "temperature_unit": "F", "district": "Pune", "village": "Shirur", "lat": 18.83, "lng": 74.37,
          "suspected_disease": "Foot-and-Mouth Disease (FMD)"}


# ---- health ---------------------------------------------------------------------------
async def test_health_and_probes(client):
    res = await client.get("/health")
    assert res.status_code == 200 and res.json()["service"] == "Pashu-Shield API"
    assert (await client.get("/live")).status_code == 200
    ready = await client.get("/ready")
    assert ready.status_code == 200 and ready.json()["checks"]["database"] == "ok"
    assert res.headers["x-content-type-options"] == "nosniff" and "x-request-id" in res.headers


# ---- auth ------------------------------------------------------------------------------
async def test_demo_login_roles(client):
    for role, expected in [("farmer", "FARMER"), ("veterinarian", "VETERINARIAN"), ("lab", "LAB_TECHNICIAN"), ("district", "DISTRICT_OFFICER")]:
        assert (await login(client, role))["user"]["role"] == expected


async def test_old_bypass_passwords_rejected(client):
    for pw in ("Govt@123", "Admin@123", "Farmer@123"):
        res = await client.post("/api/v1/auth/login", json={"email": "district.demo@pashushield.local", "password": pw})
        assert res.status_code == 401


async def test_password_login_refresh_rotation_and_reuse_detection(client):
    res = await client.post("/api/v1/auth/login", json={"email": "farmer.demo@pashushield.local", "password": DEMO_PASSWORD})
    assert res.status_code == 200
    rt1 = res.json()["refresh_token"]
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert r2.status_code == 200
    rt2 = r2.json()["refresh_token"]
    assert rt2 != rt1
    # reuse of rotated token => whole family revoked
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})).status_code == 401
    assert (await client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})).status_code == 401


async def test_logout_revokes_access_token(client):
    tok = (await login(client, "farmer"))["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 200
    assert (await client.post("/api/v1/auth/logout", headers=h)).status_code == 200
    assert (await client.get("/api/v1/auth/me", headers=h)).status_code == 401


async def test_government_signup_cannot_self_escalate(client):
    res = await client.post("/api/v1/auth/signup/government", json={
        "full_name": "Test Officer", "email": f"o{uuid.uuid4().hex[:6]}@example.gov.in", "phone": "9" + str(uuid.uuid4().int)[:9],
        "password": "Str0ng!Passw0rd", "department": "AH", "designation": "Officer", "jurisdiction": "State", "district": "Pune", "role": "SYSTEM_ADMIN"})
    assert res.status_code == 200, res.text
    user = res.json()["user"]
    assert user["role"] == "DISTRICT_OFFICER" and user["is_verified"] is False
    h = {"Authorization": f"Bearer {res.json()['access_token']}"}
    # unverified officers cannot read surveillance data
    assert (await client.get("/api/v1/surveillance/overview", headers=h)).status_code == 403


async def test_weak_password_rejected(client):
    res = await client.post("/api/v1/auth/signup/farmer", json={"full_name": "F", "phone": "9876543210", "password": "123", "district": "Pune", "village": "X"})
    assert res.status_code in (400, 422)


async def test_invalid_token_rejected(client):
    assert (await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})).status_code == 401


# ---- RBAC ------------------------------------------------------------------------------
async def test_anonymous_writes_rejected(client):
    assert (await client.post("/api/v1/reports", json=REPORT)).status_code == 401
    assert (await client.post("/api/v1/sync/push", json={"items": []})).status_code == 401
    assert (await client.get("/api/v1/sync/pull")).status_code == 401


async def test_farmer_cannot_access_lab_or_audit(client):
    h = await auth_headers(client, "farmer")
    assert (await client.get("/api/v1/labs/samples", headers=h)).status_code == 403
    assert (await client.get("/api/v1/audit/logs", headers=h)).status_code == 403
    assert (await client.get("/api/v1/surveillance/overview", headers=h)).status_code == 403


async def test_district_officer_cannot_widen_jurisdiction(client):
    h = await auth_headers(client, "district")
    assert (await client.get("/api/v1/reports?district=Nagpur", headers=h)).status_code == 403
    assert (await client.get("/api/v1/reports?district=Pune", headers=h)).status_code == 200


# ---- reporting pipeline ------------------------------------------------------------------
async def test_report_triage_case_dispatch_pipeline(client):
    h = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/reports", json=REPORT, headers=h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["triage"]["risk_level"] == "CRITICAL"
    assert data["triage"]["is_diagnosis"] is False
    assert data["triage"]["temperature_c"] == pytest.approx(40.6, abs=0.1)
    assert data["report"]["evidenceLabel"] in ("REPORTED", "UNDER VERIFICATION")
    case = data["assignedCase"]
    assert case is not None
    vet = case["assignedVet"]
    assert vet is not None and vet["vet_id"] == "DEMO-VET-001"
    assert vet["eta_status"] == "ETA_UNAVAILABLE"  # no fabricated ETA without a routing provider

    vh = await auth_headers(client, "veterinarian")
    acc = await client.post(f"/api/v1/cases/{case['caseId']}/accept", headers=vh)
    assert acc.status_code == 200, acc.text
    # invalid transition rejected
    bad = await client.patch(f"/api/v1/cases/{case['caseId']}/status", json={"status": "CLOSED"}, headers=vh)
    assert bad.status_code == 409
    ok = await client.patch(f"/api/v1/cases/{case['caseId']}/status", json={"status": "EN_ROUTE"}, headers=vh)
    assert ok.status_code == 200


async def test_temperature_implausible_rejected(client):
    h = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/reports", json={**REPORT, "temperature": 60, "temperature_unit": "C"}, headers=h)
    assert res.status_code == 422


async def test_zero_coordinates_rejected(client):
    h = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/reports", json={**REPORT, "lat": 0, "lng": 0}, headers=h)
    assert res.status_code == 422


async def test_idempotent_report_submission(client):
    h = {**(await auth_headers(client, "farmer")), "Idempotency-Key": f"idem-{uuid.uuid4().hex}"}
    r1 = await client.post("/api/v1/reports", json=REPORT, headers=h)
    r2 = await client.post("/api/v1/reports", json=REPORT, headers=h)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["report"]["id"] == r2.json()["report"]["id"]
    r3 = await client.post("/api/v1/reports", json={**REPORT, "number_affected": 9}, headers=h)
    assert r3.status_code == 422


# ---- lab workflow ------------------------------------------------------------------------
async def test_lab_workflow_verify_and_custody(client):
    vh = await auth_headers(client, "veterinarian")
    res = await client.post("/api/v1/labs/samples", json={"species": "Cattle", "disease_suspected": "FMD", "sample_type": "Blood", "district": "Pune", "tests": ["RT-PCR"]}, headers=vh)
    assert res.status_code == 200, res.text
    sid = res.json()["sample_id"]
    lh = await auth_headers(client, "lab")
    assert (await client.patch(f"/api/v1/labs/samples/{sid}/status", json={"status": "TESTING"}, headers=lh)).status_code == 200
    samples = (await client.get("/api/v1/labs/samples", headers=lh)).json()
    test_id = next(s for s in samples if s["id"] == sid)["tests"][0]["id"]
    r = await client.patch(f"/api/v1/labs/samples/{sid}/tests", json={"test_id": test_id, "status": "Completed", "result": "Positive"}, headers=lh)
    assert r.status_code == 200 and r.json()["result_version"] == 1
    v = await client.post(f"/api/v1/labs/samples/{sid}/verify", json={"remarks": "Confirmed"}, headers=lh)
    assert v.status_code == 200 and v.json()["final_result"] == "POSITIVE"
    custody = (await client.get(f"/api/v1/labs/samples/{sid}/custody", headers=lh)).json()
    assert [e["eventType"] for e in custody][:2] == ["COLLECTED", "RECEIVED"]
    # correction of a verified result requires a reason
    r2 = await client.patch(f"/api/v1/labs/samples/{sid}/tests", json={"test_id": test_id, "status": "Completed", "result": "Negative"}, headers=lh)
    assert r2.status_code == 409


# ---- offline sync ------------------------------------------------------------------------
async def test_sync_push_idempotent_and_pull_cursor(client):
    h = await auth_headers(client, "farmer")
    key = f"sync-{uuid.uuid4().hex}"
    item = {"idempotency_key": key, "store": "reports", "id": f"local-{uuid.uuid4().hex[:8]}", "operation": "CREATE",
            "data": {"species": "Goat", "numberAffected": 2, "symptoms": ["Cough"], "district": "Pune", "village": "Shirur"}}
    r1 = await client.post("/api/v1/sync/push", json={"items": [item]}, headers=h)
    assert r1.status_code == 200 and r1.json()["processed"][0]["status"] == "SYNCED", r1.text
    r2 = await client.post("/api/v1/sync/push", json={"items": [item]}, headers=h)
    assert r2.json()["processed"][0]["status"] == "ALREADY_SYNCED"
    assert r2.json()["processed"][0]["serverId"] == r1.json()["processed"][0]["serverId"]

    page = await client.get("/api/v1/sync/pull?store=reports&limit=1", headers=h)
    assert page.status_code == 200
    body = page.json()
    assert len(body["reports"]) == 1 and "cursors" in body
    if body["has_more"]["reports"]:
        nxt = await client.get(f"/api/v1/sync/pull?store=reports&limit=1&cursor={body['cursors']['reports']}", headers=h)
        assert nxt.json()["reports"][0]["id"] != body["reports"][0]["id"]


async def test_sync_version_conflict_is_persisted(client):
    h = await auth_headers(client, "farmer")
    upd = lambda k, v, base: {"idempotency_key": k, "store": "animals", "id": "DEMO-ANM-001", "operation": "UPDATE", "base_version": base, "data": {"healthStatus": v}}  # noqa: E731
    r1 = await client.post("/api/v1/sync/push", json={"items": [upd(f"a-{uuid.uuid4().hex}", "Sick", None)]}, headers=h)
    assert r1.json()["processed"][0]["status"] == "SYNCED", r1.text
    r2 = await client.post("/api/v1/sync/push", json={"items": [upd(f"b-{uuid.uuid4().hex}", "Recovered", 1)]}, headers=h)
    p = r2.json()["processed"][0]
    assert p["status"] == "CONFLICT" and "health_status" in p["conflictingFields"]
    conflicts = (await client.get("/api/v1/sync/conflicts", headers=h)).json()
    assert any(c["id"] == p["conflictId"] for c in conflicts)
    res = await client.post(f"/api/v1/sync/conflicts/{p['conflictId']}/resolve", json={"resolution": "KEEP_CLIENT"}, headers=h)
    assert res.status_code == 200 and res.json()["status"] == "RESOLVED_CLIENT"


# ---- provenance / no fabricated data -------------------------------------------------------
async def test_surveillance_has_no_padded_values(client):
    h = await auth_headers(client, "state")
    ov = (await client.get("/api/v1/surveillance/overview", headers=h)).json()
    labels = {k["label"]: k for k in ov["kpis"]}
    assert labels["Total Livestock Population"]["value"] is None
    assert labels["Total Livestock Population"]["provenance"] == "NOT_IMPORTED"
    trends = (await client.get("/api/v1/surveillance/trends", headers=h)).json()
    assert all(t["recovered"] is None for t in trends)


async def test_gis_layers_have_no_hardcoded_clusters(client):
    h = await auth_headers(client, "state")
    layers = (await client.get("/api/v1/gis/layers", headers=h)).json()
    assert all(not c.get("id", "").startswith("CL-0") for c in layers["outbreak_clusters"])
    route = (await client.get("/api/v1/gis/route?start_lat=18.5&start_lng=73.8&dest_lat=18.8&dest_lng=74.3", headers=h)).json()
    assert route["eta_status"] == "ETA_UNAVAILABLE" and route["estimated_travel_minutes"] is None


async def test_ml_prediction_labels_and_insufficient_data(client):
    h = await auth_headers(client, "state")
    res = (await client.post("/api/v1/v1/ml/predict", json={"disease": "LSD"}, headers=h)).json()
    assert res["status"] == "INSUFFICIENT_DATA"
    fc = (await client.post("/api/v1/v1/ml/forecast", json={"historical_cases": [1, 2, 3]}, headers=h)).json()
    assert fc["status"] == "INSUFFICIENT_DATA"
    perf = (await client.get("/api/v1/v1/ml/performance")).json()
    assert "SYNTHETIC" in str(perf).upper()


async def test_voice_intent_no_fabricated_lab_sample(client):
    h = await auth_headers(client, "farmer")
    res = (await client.post("/api/v1/voice/intent", json={"transcript": "check my lab sample", "language": "en"}, headers=h)).json()
    assert "SMP-10231" not in res["fulfillment_text"]


# ---- voice channel & translation provenance --------------------------------------------
async def test_voice_channel_recorded_and_server_channels_not_claimable(client):
    h = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/reports", json={**REPORT, "channel": "VOICE"}, headers=h)
    assert res.status_code == 200, res.text
    body = res.json()
    rid = body.get("reportId") or body.get("id") or (body.get("report") or {}).get("id")
    assert rid, body
    stored = await client.get(f"/api/v1/reports/{rid}", headers=h)
    assert stored.json()["source"] == "VOICE"
    bad = await client.post("/api/v1/reports", json={**REPORT, "channel": "DEMO"}, headers=h)
    assert bad.status_code == 422


async def test_translation_without_provider_is_labelled_partial(client):
    h = await auth_headers(client, "farmer")
    res = await client.post("/api/v1/voice/translate", json={"text": "cow has fever", "source_lang": "en", "target_lang": "mr"}, headers=h)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "FALLBACK_GLOSSARY_PARTIAL"
