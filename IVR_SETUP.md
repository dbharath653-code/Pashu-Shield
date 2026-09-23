# Inbound IVR (Twilio) — Setup & Operations

Pashu-Shield answers real phone calls on a Twilio number, walks the farmer through
language selection and an 8-question DTMF survey (or bridges a live vet), and creates
the **existing** `DiseaseReport` → **existing** `triage_service` → `CallbackRequest` /
vet-workflow records that the dashboards already consume.

```
Farmer phone ──► Twilio number ──► webhook POST /api/v1/telephony/inbound
                                        │  (X-Twilio-Signature validated, fail-closed)
                                        ▼
                              FastAPI telephony router (TwiML only)
                                        │
                 ┌──────────────────────┴───────────────────────┐
        Path A: vet available                        Path B: vet unavailable
        <Dial> VeterinarianProfile.number            automated DTMF survey (8 Qs)
        (recording + status callbacks)               validate → repeat/back/cancel
                 │                                           │
        call completed → optional                       finalize_survey()
        Whisper STT → rule-based                        DiseaseReport(source="IVR")
        extraction → AI/template summary                triage_service (unchanged)
                 │                                       CallbackRequest (priority=severity)
                 └──────────── CallSession (single row, state machine, district scope) ────┘
```

## 1. Configuration (`.env`)

See `.env.example`. Required for a real number:

| Variable | Purpose |
|---|---|
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Webhook signature validation + outbound API. **Never commit real values.** |
| `TWILIO_PHONE_NUMBER` | Your Twilio number in E.164 (`+1...`). |
| `TELEPHONY_PROVIDER=twilio` | `twilio` (real) or `mock` (tests / `DEMO_MODE`). |
| `TWILIO_VALIDATE_WEBHOOK` | `true` in production — rejects unsigned/foreign webhooks (fail-closed). Tests set it with fake creds. |
| `PUBLIC_API_BASE_URL` | Public HTTPS origin Twilio will reach (e.g. `https://your-deployment.example.com`). Used to reconstruct the signed URL. |
| `IVR_ENABLED` | `false` disables all `/api/v1/telephony/*` routes (503 `IVR_DISABLED`). |
| `IVR_DEFAULT_LANGUAGE` | Fallback language (`en`). Supported: `en hi mr te kn ta gu bn`. |
| `IVR_VET_TIMEOUT_SECONDS` / `IVR_MAX_VET_ATTEMPTS` | `<Dial timeout>` and bridge retry budget. |
| `CALL_RECORDING_ENABLED` | Adds `<Record>` for Path A conversations. |
| `STT_PROVIDER` / `OPENAI_API_KEY` / `AI_SUMMARY_*` | Optional Path A transcription + summary. Unconfigured → honest `NOT_CONFIGURED` summary, call still completes. |
| `DEMO_MODE` | Enables `POST /api/v1/telephony/demo/simulate` (MockTelephonyProvider). Responses are labelled **DEMO / SIMULATED**. |

`ENVIRONMENT=production` refuses to start if `TELEPHONY_PROVIDER=twilio` is selected
without Account SID/auth token/number, if `PUBLIC_API_BASE_URL` is missing, or if
`TWILIO_VALIDATE_WEBHOOK=false`.

## 2. Twilio Console (real number)

1. Buy/assign your number → **Voice Configuration → A call comes in**:
   - Webhook: `https://<your-public-host>/api/v1/telephony/inbound`
   - Method: **HTTP POST**
2. **Manage numbers → your number → Advanced** (optional Path A):
   - *A call status changes* → `https://<your-public-host>/api/v1/telephony/status` (POST)
   - *Recording a call completed* → `https://<your-public-host>/api/v1/telephony/recording` (POST)
3. Keep the **Auth Token** on the server only (env var). Trial numbers can receive
   calls only from verified caller IDs — verify your own phone for the first test.

All follow-up webhooks Twilio issues mid-call (language menu, survey answers, dial
status) are issued against URLs embedded in the returned TwiML — no extra console
config is needed for the survey flow.

## 3. Local development against a real number

Twilio must reach your machine over HTTPS. Use a tunnel:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
ngrok http 8000            # or: cloudflared tunnel --url http://localhost:8000
```

Set `PUBLIC_API_BASE_URL=https://<tunnel-host>` so signature verification
reconstructs the exact URL Twilio signed. Then point the number's webhook at
`https://<tunnel-host>/api/v1/telephony/inbound` and call it.

Signature rule: Twilio signs the **full URL including the query string** with the
raw `application/x-www-form-urlencoded` body params (sorted). Query params are used
for routing (`?step=`, `?q=`, `?r=`) but are **not** part of the signature input —
that matches Twilio's `RequestValidator` behaviour exactly.

## 4. The flow, step by step

| Webhook | Returns |
|---|---|
| `POST /api/v1/telephony/inbound` | Welcome `<Say>` + `<Gather>` language menu (DTMF 1–8). Creates `CallSession` (unique on `CallSid` — Twilio retries are idempotent). |
| `POST /api/v1/telephony/ivr?step=lang` | Stores language → greeting → Path A or Path B decision. |
| Path B `?step=survey&q=<question>` | One validated answer per hit; invalid → re-ask ×3 then skip/abort per question policy; `repeat`/`back`/`cancel`/confirm (1/2/9) always available. |
| `POST /api/v1/telephony/survey?step=confirm` | Final confirmation → `finalize_survey()` → **existing** `DiseaseReportCreate` (source `IVR`, suspected disease `Unknown`, notes carry call+survey IDs) → **existing** `triage_service` → `CallbackRequest` when warranted. |
| Path A `?step=vet_dial` | `<Dial>` to an on-duty `VeterinarianProfile` (availability API, no hardcoded vets) with `statusCallback`/`statusCallbackEvent`; no vet → back to Path B. On completed bridge: optional Whisper STT + extraction + summary attached to the same `CallSession`. |
| `POST /api/v1/telephony/status` / `/recording` | CallSession state machine + recording metadata (URL never exposed, processed/cleaned up by background jobs). |

Every response is TwiML (`Content-Type: application/xml`). Signature failure → `401`,
unknown `CallSid` on follow-ups → `404`, `IVR_ENABLED=false` → `503`.

**Correlation:** every log line and Event carries the `CallSid` → `CallSession.id`;
state transitions emit `call.started / language_selected / survey_*
/ vet_dial / report_created / callback_requested / call.completed`; district from the
farmer profile/report scopes both the WebSocket stream and the dashboard queries.
Auth tokens and full phone numbers are never logged.

## 5. Vet dashboard

**Veterinary Response → "IVR & Calls" tab**: active calls, call history (expandable
detail: survey answers, transcript, AI summary, report/callback links), callback
queue (accept / call back / create case / complete), and — only when `DEMO_MODE` —
**Simulate Incoming Farmer Call** buttons (MockTelephonyProvider, purple
**DEMO / SIMULATED** label, never a Twilio API call). Phone numbers are masked
unless the viewer has PII permission; transcript/recording endpoints are RBAC-checked
and audited; recordings expose metadata only, never a URL.

## 6. Without Twilio (tests / demo)

- `TELEPHONY_PROVIDER=mock` signs requests with `X-Mock-Signature` (HMAC-SHA256 of the
  canonical URL over the shared token) — used by `tests/test_telephony.py`.
- `DEMO_MODE=true` + `POST /api/v1/telephony/demo/simulate` (vet/para_vet only)
  drives the whole state machine in-process.
- Both are labelled simulated. `TELEPHONY_PROVIDER=none` (default) → 503.

## 7. Security checklist

- [x] Twilio signature validation, fail-closed (`RequestValidator`)
- [x] Idempotent CallSid handling (unique index + state-machine no-op retries)
- [x] RBAC + district jurisdiction on calls / transcripts / recordings / callbacks
- [x] Phone masking for viewers without PII permission; no recording URL ever served
- [x] Access audits on transcript/recording reads
- [x] No credentials in the repo — `.env.example` placeholders only
- [x] Client-supplied `user_id`/`role`/`district` never trusted (session-token claims only)
- [x] No fabricated clinical fields — unknown answers stored as `null`; suspected
      disease stays `Unknown` until a veterinarian confirms

## 8. Status honesty (see final report categories)

- **Live and testable locally:** webhook → TwiML → survey → `DiseaseReport` → triage →
  callbacks → dashboards, plus mock provider, demo simulate, full test suite
  (`pytest tests/ -q`).
- **Requires your credentials:** real Twilio signature validation with your Auth Token.
- **Requires a public HTTPS webhook:** the first real-phone milestone (tunnel or deploy).
- **Requires `OPENAI_API_KEY`:** Whisper transcripts / AI summaries (template fallback otherwise).
- **Not implemented:** outbound vet-notification calls *before* an inbound call arrives
  (vet is bridged during Path A; callbacks are queued in-app, not auto-dialed).
