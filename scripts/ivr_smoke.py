#!/usr/bin/env python3
"""Live IVR smoke test: real HTTP against a running uvicorn, with real Exotel webhook shape.

Exotel does not sign its ExoML/StatusCallback webhooks, so the trust anchor is the shared
``EXOTEL_WEBHOOK_SECRET`` carried in the ``?t=`` query parameter of every action URL — the
same shape Exotel replays back to us. This script therefore exercises exactly what the real
provider sends.

Usage (two terminals):

    # terminal 1
    ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:///./smoke.db \
      SEED_DEMO_DATA=true ENABLE_DEMO_LOGIN=true DEMO_USER_PASSWORD='Demo-Passw0rd!2026' \
      TELEPHONY_PROVIDER=exotel EXOTEL_ENABLED=true \
      EXOTEL_API_KEY=x EXOTEL_API_TOKEN=x EXOTEL_ACCOUNT_SID=x EXOTEL_PHONE_NUMBER=08047491899 \
      EXOTEL_WEBHOOK_SECRET='smoke-secret-0123456789abcdef0123456789' \
      PUBLIC_API_BASE_URL=http://127.0.0.1:8137 IVR_ENABLED=true \
      uvicorn backend.main:app --port 8137

    # terminal 2
    PASHU_SMOKE_SECRET='smoke-secret-0123456789abcdef0123456789' python scripts/ivr_smoke.py
"""
import os
import uuid

import httpx

BASE = os.environ.get("PASHU_SMOKE_BASE", "http://127.0.0.1:8137")
SECRET = os.environ.get("PASHU_SMOKE_SECRET", "smoke-secret-0123456789abcdef0123456789")
EXOPHONE = os.environ.get("PASHU_SMOKE_EXOPHONE", "08047491899")
UNKNOWN_FROM = "+919876543210"
REGISTERED_FROM = "+919000000001"   # demo farmer -> Pune -> an eligible vet exists
C = httpx.Client(base_url=BASE, timeout=20)

passed, failed = [], []


def ok(name, cond, extra=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" | {extra}" if extra else ""))


def call_sid():
    return uuid.uuid4().hex          # Exotel call ids are alpha-numeric


def exotel_post(path, params, query="", expect=200, secret=SECRET, send_secret=True):
    qs = [p for p in (query, f"t={secret}" if (send_secret and secret) else "") if p]
    url = f"/api/v1/ivr/{path}" + (f"?{'&'.join(qs)}" if qs else "")
    r = C.post(url, data=params)
    body = r.text
    assert r.status_code == expect, f"{path} -> {r.status_code}: {body[:400]}"
    if expect == 200:
        assert "xml" in r.headers.get("content-type", ""), r.headers
        assert body.startswith('<?xml version="1.0" encoding="UTF-8"?>'), body[:200]
        assert "<Response>" in body[:200], body[:200]
    return body


def login(role):
    r = C.post(f"/api/v1/auth/demo-login/{role}")
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- 1. webhook trust ----------------------------------------------------------------------
sid0 = call_sid()
r = C.post("/api/v1/ivr/incoming", data={"CallSid": sid0, "From": UNKNOWN_FROM})
ok("webhook without secret rejected 401", r.status_code == 401, str(r.status_code))
r = C.post("/api/v1/ivr/incoming?t=not-the-real-secret", data={"CallSid": sid0, "From": UNKNOWN_FROM})
ok("webhook with wrong secret rejected 401", r.status_code == 401, str(r.status_code))
r = C.post(f"/api/v1/ivr/incoming?t={SECRET}", data={"From": UNKNOWN_FROM})
ok("webhook without CallSid rejected 400", r.status_code == 400, str(r.status_code))

# ---- 2. inbound welcome + duplicate idempotency ---------------------------------------------
sid = call_sid()
b1 = exotel_post("incoming", {"CallSid": sid, "From": UNKNOWN_FROM, "To": EXOPHONE,
                              "Direction": "incoming"})
ok("inbound returns ExoML welcome + language Gather",
   "Welcome to Pashu Shield" in b1 and "<Gather" in b1 and "Press 1 for English" in b1)
b2 = exotel_post("incoming", {"CallSid": sid, "From": UNKNOWN_FROM, "To": EXOPHONE})
ok("duplicate inbound webhook is idempotent", "Welcome to Pashu Shield" in b2)

# ---- 3. language -> main menu ---------------------------------------------------------------
b3 = exotel_post("input", {"CallSid": sid, "digits": "1"}, query="step=language")
ok("language 1 -> main menu", "Press 1 to report a sick animal" in b3 and "<Gather" in b3)
b3b = exotel_post("input", {"CallSid": sid, "digits": "7"}, query="step=menu")
ok("invalid menu digit re-asks", "not a valid option" in b3b and "Press 1 to report a sick animal" in b3b)
b3c = exotel_post("input", {"CallSid": sid, "digits": "1"}, query="step=menu")
ok("menu 1 -> survey Q1", "What animal is affected" in b3c)

# ---- 4. invalid DTMF re-asks -----------------------------------------------------------------
b4 = exotel_post("input", {"CallSid": sid, "digits": "9"}, query="step=survey&q=species")
ok("invalid species re-asks", "What animal is affected" in b4 and "not a valid option" in b4)

# ---- 5. full survey ---------------------------------------------------------------------------
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
    last = exotel_post("input", {"CallSid": sid, "digits": digits}, query=f"step=survey&q={q}")
    ok(f"survey {q} -> next prompt contains {expect!r}", expect in last.lower() or expect in last,
       last[:90].replace("\n", " "))
ok("final confirmation says goodbye", "goodbye" in last.lower())

# replaying the confirmation must not create a second report
replay = exotel_post("input", {"CallSid": sid, "digits": "1"}, query="step=survey&q=confirm")
ok("confirmation replay does not re-submit", "Goodbye" in replay)

# ---- 6. PATH A: registered farmer asks for a veterinarian --------------------------------------
sidA = call_sid()
exotel_post("incoming", {"CallSid": sidA, "From": REGISTERED_FROM, "To": EXOPHONE})
exotel_post("input", {"CallSid": sidA, "digits": "1"}, query="step=language")
bA = exotel_post("input", {"CallSid": sidA, "digits": "2"}, query="step=menu")
ok("menu 2 -> ExoML <Dial> to a veterinarian", "<Dial" in bA and "<Number>" in bA,
   bA[:160].replace("\n", " "))
bA2 = exotel_post("input", {"CallSid": sidA, "DialCallStatus": "no-answer"}, query="step=vet_dial")
ok("vet no-answer falls back to the survey", "What animal is affected" in bA2)

# ---- 7. case status is refused for an unverified caller ----------------------------------------
sidC = call_sid()
exotel_post("incoming", {"CallSid": sidC, "From": UNKNOWN_FROM, "To": EXOPHONE})
exotel_post("input", {"CallSid": sidC, "digits": "1"}, query="step=language")
bC = exotel_post("input", {"CallSid": sidC, "digits": "3"}, query="step=menu")
ok("menu 3 for unknown caller discloses nothing", "could not match this number" in bC)

# ---- 8. StatusCallback -------------------------------------------------------------------------
bS = exotel_post("status", {"CallSid": sidA, "Status": "completed", "ConversationDuration": "180",
                            "RecordingUrl": "https://recordings.exotel.com/exotelrecordings/x.mp3",
                            "EventType": "terminal"})
ok("StatusCallback acknowledged with an empty document", bS.strip().startswith("<?xml") and "<Gather" not in bS)
r = C.post(f"/api/v1/ivr/status?t={SECRET}", data={"CallSid": call_sid(), "Status": "completed"})
ok("StatusCallback for an unknown call id -> 404", r.status_code == 404, str(r.status_code))

# ---- 9. DEMO_MODE simulation --------------------------------------------------------------------
vet = login("veterinarian")
r = C.post("/api/v1/telephony/demo/simulate", json={"language": "en", "scenario": "vet_unavailable"},
           headers=vet)
ok("demo simulate works for a vet", r.status_code == 200, f"status={r.status_code} body={r.text[:200]}")
if r.status_code == 200:
    sim = r.json()
    ok("simulate is labelled DEMO / SIMULATED and returns a report",
       sim.get("label") == "DEMO / SIMULATED" and bool(sim.get("reportId")), sim.get("label", ""))

# ---- 10. dashboards + RBAC + district scoping -----------------------------------------------------
r = C.get("/api/v1/telephony/calls?limit=50", headers=vet)
ok("vet dashboard lists calls", r.status_code == 200 and len(r.json()) >= 1, f"status={r.status_code}")
calls = r.json() if r.status_code == 200 else []
vet_sids = {c.get("callSid") for c in calls}
ok("vet sees district (Pune) calls incl. PATH A", sidA in vet_sids, str(sorted(vet_sids))[:200])
ok("vet does NOT see the unknown-location call", sid not in vet_sids)
row = next((c for c in calls if c.get("callSid") == sidA), None)
ok("call row carries the Exotel channel + menu choice",
   bool(row) and row.get("provider") == "exotel" and row.get("ivrMenuOption") == "2",
   str({k: row.get(k) for k in ("provider", "ivrMenuOption", "isEmergency")} if row else None))

try:
    admin = login("state")
except AssertionError:
    admin = login("admin")
ar = C.get("/api/v1/telephony/calls?limit=50", headers=admin)
ok("state/admin sees all calls incl. unknown-location",
   ar.status_code == 200 and sid in {c.get("callSid") for c in ar.json()}, f"status={ar.status_code}")

r = C.get("/api/v1/callbacks?limit=50", headers=vet)
ok("callback queue readable", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    print(f"INFO vet-visible callbacks={len(r.json())} "
          f"priorities={[c.get('priority') for c in r.json()][:5]}")

# The unknown-caller survey callback has district "Unknown" (we never guess a location), so
# by design it is NOT in a district-scoped vet's queue — it waits for state/admin to place it.
ar = C.get("/api/v1/callbacks?limit=50", headers=admin)
admin_cbs = ar.json() if ar.status_code == 200 else []
unlocated = [c for c in admin_cbs if not c.get("district") or c.get("district") == "Unknown"]
ok("unknown-location callback is held for state/admin (not a district vet)",
   ar.status_code == 200 and len(unlocated) >= 1
   and not any(c.get("district") == "Unknown" for c in (r.json() if r.status_code == 200 else [])),
   f"admin_status={ar.status_code} admin_total={len(admin_cbs)} unlocated={len(unlocated)}")

if row:
    d = C.get(f"/api/v1/telephony/calls/{row['id']}", headers=vet)
    ok("call detail readable by a vet", d.status_code == 200, f"status={d.status_code}")

farmer = login("farmer")
r = C.get("/api/v1/telephony/calls", headers=farmer)
ok("farmer list restricted to own calls",
   r.status_code == 200 and all(c.get("farmerId") == "DEMO-FARMER-001" for c in r.json()),
   f"status={r.status_code} n={len(r.json()) if r.status_code == 200 else '-'}")
r = C.post("/api/v1/telephony/demo/simulate", json={"scenario": "vet_unavailable"}, headers=farmer)
ok("farmer blocked from simulate", r.status_code in (401, 403), str(r.status_code))

print("\n==== IVR SMOKE SUMMARY ====")
print(f"passed={len(passed)} failed={len(failed)}")
if failed:
    print("FAILURES:")
    for name in failed:
        print(" -", name)
    raise SystemExit(1)
print("ALL LIVE IVR SMOKE CHECKS PASSED")
