#!/usr/bin/env python3
"""Live smoke test: real HTTP + real Twilio HMAC signature validation against uvicorn."""
import hashlib
import hmac
import json
import uuid

import httpx

BASE = "http://127.0.0.1:8137"
TOKEN = "test-auth-token-0123456789abcdef0123456789"
UNKNOWN_FROM = "+919876543210"
REGISTERED_FROM = "+919000000001"  # demo farmer -> Pune -> eligible vet exists
C = httpx.Client(base_url=BASE, timeout=15)

passed, failed = [], []


def ok(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" | {extra}" if extra else ""))


def sign(url, params):
    # Twilio: base64(HMAC-SHA256(URL + sorted key+value concat)) — use the official SDK
    from twilio.request_validator import RequestValidator
    return RequestValidator(TOKEN).compute_signature(url, params)


def twiml_post(path, params, query="", expect=200):
    full_path = path + (f"?{query}" if query else "")
    url = BASE + full_path
    r = C.post(full_path, data=params, headers={"X-Twilio-Signature": sign(url, params)})
    body = r.text
    assert r.status_code == expect, f"{path} -> {r.status_code}: {body[:400]}"
    if expect == 200:
        assert "xml" in r.headers.get("content-type", ""), r.headers
        assert "<Response" in body[:300], body[:300]
    return body


def login(role):
    r = C.post(f"/api/v1/auth/demo-login/{role}")
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- 1. signature rejection ----
sid0 = "CA" + uuid.uuid4().hex[:14]
r = C.post("/api/v1/telephony/inbound", data={"CallSid": sid0, "From": UNKNOWN_FROM})
ok("unsigned webhook rejected 401", r.status_code == 401, str(r.status_code))
url = BASE + "/api/v1/telephony/inbound"
bad = hmac.new(b"wrong", (url + "CallSid" + sid0).encode(), hashlib.sha256).hexdigest()
r = C.post("/api/v1/telephony/inbound", data={"CallSid": sid0, "From": UNKNOWN_FROM},
           headers={"X-Twilio-Signature": bad})
ok("wrong-token signature rejected 401", r.status_code == 401, str(r.status_code))

# ---- 2. inbound welcome + duplicate idempotency ----
sid = "CA" + uuid.uuid4().hex[:14]
b1 = twiml_post("/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
ok("inbound welcome TwiML", "Welcome to Pashu Shield" in b1 and "<Gather" in b1)
b2 = twiml_post("/api/v1/telephony/inbound", {"CallSid": sid, "From": UNKNOWN_FROM})
ok("duplicate inbound idempotent (welcome again)", "Welcome to Pashu Shield" in b2)

# ---- 3. language selection ----
b3 = twiml_post("/api/v1/telephony/ivr", {"CallSid": sid, "Digits": "1"})
ok("language 1 -> survey Q1", "What animal is affected" in b3 and "<Gather" in b3, b3[:120].replace("\n", " "))

# ---- 4. invalid DTMF re-asks ----
b4 = twiml_post("/api/v1/telephony/survey", {"CallSid": sid, "Digits": "9"}, query="q=species")
ok("invalid species re-asks + says not valid", "What animal is affected" in b4 and "not a valid option" in b4)

# ---- 5. full survey ----
seq = [
    ("1", "species", "How many animals"),
    ("4", "affected_count", "symptom"),
    ("12", "symptoms", "day"),
    ("2", "duration", "died"),
    ("0", "deaths", "vaccin"),
    ("3", "vaccination", "location"),
    ("1", "location", "submit"),
    ("1", "confirm", "report number"),
]
last = ""
for digits, q, expect in seq:
    last = twiml_post("/api/v1/telephony/survey", {"CallSid": sid, "Digits": digits}, query=f"q={q}")
    ok(f"survey {q} -> next prompt contains {expect!r}", expect in last.lower() or expect in last,
       last[:90].replace("\n", " "))
ok("final confirmation says goodbye", "goodbye" in last.lower())

# ---- 6. report rows exist in DB (checked after path A below via dashboards) ----

# ---- 7. Path A attempt for registered farmer (eligible vet -> <Dial>) ----
sidA = "CA" + uuid.uuid4().hex[:14]
twiml_post("/api/v1/telephony/inbound", {"CallSid": sidA, "From": REGISTERED_FROM, "To": "+15005550006"})
bA = twiml_post("/api/v1/telephony/ivr", {"CallSid": sidA, "Digits": "1"})
ok("registered farmer -> Path A <Dial>", "<Dial" in bA, bA[:150].replace("\n", " "))
bA2 = twiml_post("/api/v1/telephony/ivr", {"CallSid": sidA, "DialCallStatus": "no-answer"},
                 query="step=vet_dial")
ok("vet no-answer falls back to survey", "What animal is affected" in bA2)

# ---- 8. demo simulate endpoint ----
vet = login("veterinarian")
h = {"headers": vet}
r = C.post("/api/v1/telephony/demo/simulate", json={"language": "en", "scenario": "vet_unavailable"}, **h)
ok("demo simulate works for vet", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
if r.status_code == 200:
    sim = r.json()
    ok("simulate returns report id", bool(sim.get("reportId")), sim.get("label", ""))

# ---- 9. dashboards + RBAC + district scoping (after path A call exists) ----
vet = login("veterinarian")
h = {"headers": vet}
r = C.get("/api/v1/telephony/calls?limit=50", **h)
ok("vet dashboard lists calls", r.status_code == 200 and len(r.json()) >= 1, f"status={r.status_code}")
calls = r.json() if r.status_code == 200 else []
vet_sids = {c.get("callSid") for c in calls}
ok("vet sees district (Pune) calls incl. path-A", sidA in vet_sids, str(sorted(vet_sids))[:200])
ok("vet does NOT see unknown-location call", sid not in vet_sids)

admin = login("state") if True else None
try:
    ar = C.get("/api/v1/telephony/calls?limit=50", headers=admin)
    if ar.status_code != 200:
        admin = login("admin")
        ar = C.get("/api/v1/telephony/calls?limit=50", headers=admin)
except Exception:
    admin = login("admin")
    ar = C.get("/api/v1/telephony/calls?limit=50", headers=admin)
ok("state/admin sees all calls incl. unknown-location", ar.status_code == 200 and sid in {c.get("callSid") for c in ar.json()},
   f"status={ar.status_code}")

r = C.get("/api/v1/callbacks?limit=50", **h)
ok("callback queue readable", r.status_code == 200, f"status={r.status_code}")
cbs = r.json() if r.status_code == 200 else []
print(f"INFO callbacks={len(cbs)} priorities={[c.get('priority') for c in cbs][:5]}")

found = next((c for c in calls if c.get("callSid") == sidA), None)
if found:
    r = C.get(f"/api/v1/telephony/calls/{found['id']}", **h)
    ok("call detail for vet", r.status_code == 200, f"status={r.status_code}")
    if r.status_code == 200:
        d = r.json()
        # Baseline RBAC grants VETERINARIAN PII_VIEW -> full phone (masking for non-PII
        # viewers is unit-tested in test_farmer_phone_masked_without_pii_permission).
        ok("detail honors PII policy (field present; vet PII_VIEW -> full)",
           "callerMasked" in d and d.get("callerMasked") is False and d.get("callerPhone", "").startswith("+"),
           f"masked={d.get('callerMasked')} phone={d.get('callerPhone')}")

# farmer role: 200 but ONLY own calls (ownership scoping, mirrors reports)
farmer = login("farmer")
r = C.get("/api/v1/telephony/calls", headers=farmer)
ok("farmer list restricted to own calls",
   r.status_code == 200 and all(c.get("farmerId") == "DEMO-FARMER-001" for c in r.json()),
   f"status={r.status_code} n={len(r.json()) if r.status_code == 200 else '-'}")
r = C.post("/api/v1/telephony/demo/simulate", json={"scenario": "vet_unavailable"}, headers=farmer)
ok("farmer blocked from simulate", r.status_code in (401, 403), str(r.status_code))
r = C.get("/api/v1/callbacks", headers=farmer)
ok("farmer callback list restricted to own rows",
   r.status_code == 200 and all(c.get("farmerId") == "DEMO-FARMER-001" for c in r.json()),
   f"status={r.status_code} n={len(r.json()) if r.status_code == 200 else '-'}")

print("\n==== SMOKE SUMMARY ====")
print(f"passed={len(passed)} failed={len(failed)}")
if failed:
    print("FAILURES:")
    for f_ in failed:
        print(" -", f_)
    raise SystemExit(1)
print("ALL LIVE SMOKE CHECKS PASSED")
