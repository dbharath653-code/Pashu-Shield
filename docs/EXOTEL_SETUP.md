# Inbound IVR (Exotel) — Setup & Operations

Pashu-Shield answers real phone calls on an Exotel virtual number (ExoPhone), walks the
farmer through a keypad menu, and feeds the answers into the **existing** disease-report →
triage → veterinary-case → dispatch → dashboard pipeline. No separate IVR database, case
system or triage engine exists: the telephony layer is transport only.

```
Farmer phone ──► ExoPhone ──► Exotel ExoML app ──► POST /api/v1/ivr/incoming
                                                        │ (shared webhook secret, fail-closed)
                                              FastAPI IVR router (ExoML only)
                                                        ▼
                    CallSession (idempotent on Exotel CallSid) → caller identification
                                                        ▼
        language → main menu → { report survey | veterinarian <Dial> | case status | emergency }
                                                        ▼
    DiseaseReportCreate → report_service.submit_report → TriageEngine → VeterinaryCase
                       → DispatchEngine offer → NotificationService → WebSocket dashboard
```

---

## 1. Environment variables

All Exotel settings are **backend-only**. Nothing Exotel-related is ever exposed to React or
to a `VITE_*` variable.

| Variable | Purpose |
| --- | --- |
| `TELEPHONY_PROVIDER` | `exotel` (real) or `mock` (tests / `DEMO_MODE`). |
| `EXOTEL_ENABLED` | Explicit live switch. Must be `true` with `exotel` and `false` with `mock` — the app refuses to start otherwise, so a real number can never be dialled by accident. |
| `EXOTEL_API_KEY` / `EXOTEL_API_TOKEN` | HTTP Basic Auth credentials (Dashboard → Settings → API Settings). **Never commit real values.** |
| `EXOTEL_ACCOUNT_SID` | Account identifier; a path segment in every Exotel API URL. |
| `EXOTEL_SUBDOMAIN` | Regional API host: `api.in.exotel.com` (Mumbai) or `api.exotel.com` (Singapore). Using the wrong region returns 401/404. |
| `EXOTEL_PHONE_NUMBER` | Your ExoPhone in the format Exotel shows it (e.g. `08047491899`). Used as the `callerId` on the veterinarian `<Dial>`. |
| `EXOTEL_APP_ID` | The ExoML app whose application URL points at `POST /api/v1/ivr/incoming`. |
| `EXOTEL_WEBHOOK_SECRET` | **The trust anchor.** Appended to every ExoML action URL as `?t=…` and required on every webhook. Generate with `python -c "import secrets;print(secrets.token_urlsafe(48))"`. |
| `EXOTEL_VALIDATE_WEBHOOK` | `true` in production — rejects unsigned/foreign webhooks (fail-closed). |
| `EXOTEL_VERIFY_CALL_SID` | Optional second factor: confirm an unknown `CallSid` against Exotel's authenticated Call Details API (one extra round trip per call). |
| `EXOTEL_TIMEOUT_SECONDS` | Timeout for outbound Exotel API calls (default `10`). |
| `PUBLIC_API_BASE_URL` | Public HTTPS origin Exotel reaches, e.g. `https://your-domain.ngrok-free.app`. **Required** — ExoML action URLs must be absolute. |
| `IVR_ENABLED` | `false` returns a polite "unavailable" message and hangs up — the safe way to switch the helpline off. |
| `IVR_DEFAULT_LANGUAGE`, `IVR_VET_TIMEOUT_SECONDS`, `IVR_MAX_VET_ATTEMPTS`, `CALL_RECORDING_ENABLED`, `DEMO_MODE` | Existing IVR-flow settings, unchanged by the migration. |

`ENVIRONMENT=production` refuses to start without a ≥32-character `EXOTEL_WEBHOOK_SECRET`,
with `EXOTEL_VALIDATE_WEBHOOK=false`, with a non-HTTPS `PUBLIC_API_BASE_URL`, without
`EXOTEL_APP_ID`, or with `TELEPHONY_PROVIDER=mock`.

---

## 2. Exotel account setup

1. **Create an Exotel account** at <https://exotel.com> and complete KYC.
2. **Activate the trial.** On a trial account, calls are only allowed to/from numbers you
   have verified in the dashboard — verify the phones you will test with.
3. **Obtain an ExoPhone** (Dashboard → ExoPhones). This is the number the farmer dials.
4. **Collect your credentials**: Dashboard → Settings → API Settings gives the API Key, API
   Token and Account SID. Note your region (Mumbai vs Singapore) for `EXOTEL_SUBDOMAIN`.
5. **Create the ExoML app**: Dashboard → App Bazaar → create a new app and set its
   **application URL** to

   ```
   https://<your-public-host>/api/v1/ivr/incoming?t=<EXOTEL_WEBHOOK_SECRET>
   ```

   Method: `POST`. Exotel fetches this URL when a call arrives and executes the ExoML we
   return. Note the app id from the URL/dashboard and set `EXOTEL_APP_ID`.
6. **Attach the app to the ExoPhone** so incoming calls on that number run the flow.

All follow-up requests during a call (language menu, main menu, survey answers, dial result)
go to URLs embedded in the ExoML we return — no extra dashboard configuration is needed. The
optional `StatusCallback` URL is `https://<your-public-host>/api/v1/ivr/status?t=<secret>`.

---

## 3. Local development (FastAPI + ngrok + Exotel trial)

```bash
# 1. dependencies
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# 2. configuration
cp .env.example .env            # then fill in the EXOTEL_* values
python -c "import secrets;print(secrets.token_urlsafe(48))"   # -> EXOTEL_WEBHOOK_SECRET

# 3. schema
alembic upgrade head

# 4. API
uvicorn backend.main:app --reload --port 8000

# 5. public HTTPS tunnel (Exotel cannot reach localhost)
ngrok http 8000
```

Copy the ngrok HTTPS URL into **both** `PUBLIC_API_BASE_URL` in `.env` **and** the ExoML
app's application URL, then restart uvicorn. The URL is never hardcoded anywhere in the
codebase — it is read from the environment.

### Test call procedure

1. Dial your ExoPhone from a verified number.
2. You hear the welcome line, then the language menu. Press `1` (English).
3. You hear the main menu: `1` report a sick animal, `2` speak to a veterinarian,
   `3` case status, `0` emergency.
4. Press `1` and answer the survey with the keypad (`1` Cattle, `4` animals, `12#` fever +
   loss of appetite, `2` duration, `0` deaths, `3` vaccination unknown, `1` registered
   village, `1` to submit).
5. You hear your report number and the preliminary triage level.

### Verify

| Check | Where |
| --- | --- |
| Webhooks arrived | FastAPI logs: `IVR_CALL_RECEIVED`, `IVR_SESSION_CREATED`, `IVR_MENU_SELECTED`, `IVR_INPUT_RECEIVED`, `IVR_CASE_CREATED`, `IVR_CALL_COMPLETED` (structured JSON, one line per event, carrying `call_id`, `call_session`, `report_id`, `case_id`). |
| Case created | `GET /api/v1/telephony/calls` and `GET /api/v1/reports` — the report has `source: "IVR"`. |
| Dashboard updated | Veterinary Response → Calls tab: the row shows **Channel: IVR · exotel**, the menu choice, the call id and the linked report. |
| Callback queued | Veterinary Response → Callback Queue (priority = the triage severity). |

Without a real Exotel account you can exercise the identical code path locally:

```bash
# full flow against a running server, mocked Exotel webhooks
PASHU_SMOKE_SECRET='<your EXOTEL_WEBHOOK_SECRET>' python scripts/ivr_smoke.py
```

---

## 4. API endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/ivr/incoming` | ExoML application URL. Creates the `CallSession` (unique on `CallSid`, so Exotel retries are idempotent), identifies the caller, returns welcome + language `<Gather>`. |
| `POST /api/v1/ivr/input` | Every in-call ExoML `action`. `?step=language` · `?step=menu` · `?step=survey&q=<question>` · `?step=vet_dial`. |
| `POST /api/v1/ivr/status` | Exotel `StatusCallback`. Telemetry only — records status/duration/recording URL and returns an empty document, so it can never alter a live call. |

Every response is ExoML (`application/xml`). Failure modes: `400` malformed webhook or
missing `CallSid`, `401` untrusted webhook, `404` unknown `CallSid`, `409` follow-up for a
call with no survey, `429` rate limited. A *downstream* failure (database, triage,
notifications) still returns `200` with a polite spoken message — a farmer is never left on
a silent line, and a stack trace is never spoken or returned.

---

## 5. Security

Exotel does **not** sign ExoML or StatusCallback webhooks — there is no `X-Exotel-Signature`
equivalent in the current API. Rather than invent one, the integration uses the mechanisms
Exotel actually supports, layered:

1. **Shared secret in the action URL** (`?t=…`). Exotel only ever POSTs to URLs our own ExoML
   responses produced, so possession of the token demonstrates the request came from our
   configured ExoML application. Compared in constant time; also accepted as the
   `X-Exotel-Webhook-Secret` header.
2. **CallSid correlation.** Every follow-up must reference a `CallSession` that an
   already-verified `/incoming` created; unknown ids get `404`.
3. **Optional authenticated CallSid verification** (`EXOTEL_VERIFY_CALL_SID=true`) against
   Exotel's Call Details API.
4. **Network controls**: HTTPS only (enforced in production), plus an allow-list of Exotel's
   documented egress ranges at your ingress/WAF — ask Exotel support for the current list for
   your region.

Also enforced: idempotency on the provider call id, unique `(survey_id, question)` answers,
per-call webhook rate limiting, bounded input lengths, safe phone normalisation, structured
logs that never carry a full phone number, a transcript or a credential, and recordings that
are only ever served through the RBAC-checked, audited dashboard endpoint.

**CORS** is unchanged and already safe: `CORS_ORIGINS` is an explicit comma-separated
allow-list (`http://localhost:5173` in development) and production refuses to start if it is
empty or contains `*`. Exotel webhooks are server-to-server and are not affected by CORS.

---

## 6. Without an Exotel account (tests / demo)

* `TELEPHONY_PROVIDER=mock` + `EXOTEL_ENABLED=false` runs the identical flow through
  `MockTelephonyProvider`, which speaks the same ExoML and reads the same Exotel parameter
  names. Automated tests use this path.
* `DEMO_MODE=true` enables the dashboard's **Simulate Incoming Farmer Call** action. Every
  row it creates carries `is_simulated=true` and is labelled **DEMO / SIMULATED**; it is
  refused in production. There is no silent fallback from a failed real Exotel call to
  simulated data — demo mode is always explicit.

---

## 7. Honest-data guarantees

* An unknown caller is recorded as unknown. No location is ever assumed — there is no
  Pune/Shirur (or any other) fallback anywhere in the telephony or voice layer.
* A keypad caller who is not at their registered village gets `location_status =
  LOCATION_UNAVAILABLE`, not a guessed village.
* `suspected_disease` from a phone survey is always `Unknown`. The IVR reports *symptoms*;
  the existing triage engine decides *risk*; only a veterinarian/lab produces a diagnosis.
* Pressing `0` records that the **caller** declared an emergency. It does not set risk, does
  not imply a disease, and the dashboard label says exactly that.
* A required answer that cannot be collected aborts the survey honestly and queues a
  callback instead of fabricating a value.
