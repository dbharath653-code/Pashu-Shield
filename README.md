# Pashu-Shield — Livestock Health Surveillance, Early-Warning & Veterinary Response Platform

**Pashu-Shield** is an offline-first, real-time livestock disease surveillance, outbreak early-warning, and emergency veterinary response platform built for Maharashtra state animal-husbandry operations. It combines a React 19 PWA frontend, an async FastAPI backend with PostgreSQL/PostGIS, a background job worker, an inbound phone (Twilio IVR) channel for farmers without smartphones, and on-device ML — with a strict **honest-data policy**: surveillance figures are computed only from stored records, and unconfigured integrations are shown as *unavailable*, never substituted with fabricated numbers.

- **Backend API version:** 2.1.0 (`backend/config.py`)
- **Docs:** [IVR Setup & Operations](IVR_SETUP.md) · [External Integrations Status](docs/INTEGRATIONS.md) · [Environment Variables](.env.example)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Repository Layout](#repository-layout)
3. [Backend (FastAPI)](#backend-fastapi)
4. [Inbound Telephony & IVR (Twilio)](#inbound-telephony--ivr-twilio)
5. [Background Worker & Scheduled Jobs](#background-worker--scheduled-jobs)
6. [Real-Time Events (WebSocket)](#real-time-events-websocket)
7. [Machine Learning](#machine-learning)
8. [Frontend (React 19 PWA)](#frontend-react-19-pwa)
9. [Offline-First Synchronisation](#offline-first-synchronisation)
10. [Roles & RBAC](#roles--rbac)
11. [Demo Accounts](#demo-accounts)
12. [End-to-End Workflow](#end-to-end-workflow)
13. [Local Setup & Running](#local-setup--running)
14. [Configuration & Environments](#configuration--environments)
15. [Docker Deployment](#docker-deployment)
16. [Hosting (Vercel / Netlify / GitHub Pages)](#hosting-vercel--netlify--github-pages)
17. [Testing & CI](#testing--ci)
18. [Security Posture](#security-posture)
19. [External Integrations](#external-integrations)

---

## Architecture Overview

```
                                        +---------------------------------------------------+
                                        |              Pashu-Shield Frontend (PWA)          |
                                        |  React 19 · TypeScript · Vite 8 · Tailwind 4      |
                                        |  Workbox service worker · IndexedDB · Leaflet     |
                                        |  Web Speech + Whisper-tiny (ONNX, in-browser)     |
                                        +-------------------------+-------------------------+
                                            /api/v1 REST + /api/v1/ws WebSocket (Vite dev proxy)
                                                                      |
              Farmer phone ──► Twilio ──► signed webhooks             |
                                        +-----------------------------▼---------------------+
                                        |              FastAPI Backend (async, Python 3.11) |
                                        |  18 routers · ~96 REST endpoints · JWT + RBAC     |
                                        |  Triage · Dispatch · Alert & Outbreak engines     |
                                        +----+------------------+------------------+--------+
                                             |                  |                  |
                        +--------------------▼-----+   +--------▼--------+   +-----▼---------------------+
                        | PostgreSQL 15 + PostGIS  |   | Redis 7         |   | Background Worker         |
                        | (SQLite fallback in dev) |   | rate limits +   |   | python -m backend.worker  |
                        | 37 tables · Alembic      |   | job queue       |   | notifications · expiry ·  |
                        | 3 migrations             |   | (optional)      |   | outbreak · ingest · purge |
                        +--------------------------+   +-----------------+   +---------------------------+
                                             |
        +--------------------+---------------+----------------+--------------------+
        |                    |                |                |                    |
+───────▼───────+   +────────▼───────+   +──────▼──────+   +───────▼───────+    +───────▼────────+
│ Twilio        │   │ Notifications  │   │ File store  │   │ External data │    │ ML models      │
│ voice + TwiML │   │ Fast2SMS SMS · │   │ magic-byte  │   │ NADRES · DAHD │    │ RandomForest · │
│ signature     │   │ WhatsApp Cloud │   │ validation +│   │ · Open-Meteo  │    │ IsolationForest│
│ validation    │   │ API (signed)   │   │ ClamAV scan │   │ · OSRM · labs │    │ (+ browser     │
+───────────────+   +────────────────+   +─────────────+   +───────────────+    │ fallback)      │
                                                              +────────────────+

Every provider above has a safe default: unset ⇒ endpoint reports UNAVAILABLE /
CONFIGURATION_REQUIRED. Production refuses to start with insecure or mock settings.
```

---

## Repository Layout

```
├── App.tsx                    # React router: 16 modules + dedicated per-role auth pages
├── backend/                   # FastAPI application (the only canonical API/ML implementation)
│   ├── main.py                # App factory, lifespan, WebSocket endpoint, health probes
│   ├── config.py              # Validated settings; production refuses insecure configs
│   ├── database.py            # Async SQLAlchemy 2.0 engine (PostGIS/asyncpg or aiosqlite)
│   ├── models.py              # 37 relational tables (sync-enabled, audited)
│   ├── schemas.py             # Pydantic v2 request/response models
│   ├── security.py            # bcrypt, JWT issue/verify, require_roles dependencies
│   ├── middleware.py          # Request-context (X-Request-ID), JSON logs, error envelope
│   ├── init_db.py             # Schema bootstrap + opt-in demo seeding (is_demo=true rows)
│   ├── worker.py              # `python -m backend.worker` job runner (SKIP LOCKED safe)
│   ├── routers/               # auth · users · animals · reports · cases · labs · vaccinations
│   │                          # surveillance · gis · alerts · sync · voice · external · audit
│   │                          # ml · telephony · calls · callbacks (+ external webhooks)
│   └── services/              # triage · dispatch · alert_engine · outbreak · workflow · jobs
│                              # notification · external_data · lab_integration · ml_service
│                              # translation · routing (OSRM) · spatial · idempotency · rate_limit
│                              # file_service (ClamAV) · websocket_manager · events · audit
│                              # ivr/ (prompts · question_flow · survey_engine)
│                              # telephony/ (twiml · call_router · twilio · mock · webhooks)
│                              # voice/ (transcription · extraction · call_summary)
├── migrations/                # Alembic: 0001_baseline → 0002_postgis → 0003_telephony_ivr
├── ml-backend/                # Optional thin wrapper deploying the canonical ML router
│   ├── main.py                # mounts backend.routers.ml — one implementation, two hosts
│   ├── train_model.py         # RandomForest + IsolationForest training (synthetic, versioned)
│   └── models/                # rf_model.pkl · iso_model.pkl · scaler.pkl · model_card.json
├── components/                # Layout, Sidebar, Topbar, PashuMap, PersistentVoiceAssistant,
│                              # SyncModal, ActivityFeedWidget, ErrorBoundary
├── context/                   # Auth, App, Alerts, AnimalHealth, Lab, Vaccination,
│                              # VetResponse, Multilingual providers
├── pages/                     # Dashboard, FarmerDashboard, DiseaseSurveillance, GisRiskMap,
│                              # AIEarlyWarning, CaseReporting, AnimalHealth/, VetResponse/,
│                              # LabManagement/, VaccinationManagement/, AlertsNotifications/,
│                              # Multilingual/, OfflineSync/, DiseaseInfo/, Analytics/,
│                              # Administration/, Auth/ (per-role login & signup)
├── services/                  # Frontend API layer: apiAuth (fetch wrapper + token rotation),
│                              # ReportingService, AnalyticsService, AdminService, DiseaseService,
│                              # LocalMLService, MLApiService, ReferenceData, SyncService (tsx),
│                              # IndexedDBService, AssetPaths, Dialogs
├── workers/whisperWorker.ts   # Offline speech-to-text (Xenova/whisper-tiny, quantised ONNX)
├── locales/                   # 8 UI dictionaries: en · hi · mr · te · kn · gu · ta · bn
├── public/                    # Whisper ONNX models, ONNX Runtime WASM, Maharashtra GeoJSON,
│                              # symptom dictionary, browser ML weights, PWA icons
├── tests/                     # pytest: test_backend.py · test_services.py · test_telephony.py
├── scripts/                   # smoke.mjs (headless route smoke test) · ivr_smoke.py (live Twilio)
├── docs/INTEGRATIONS.md       # Integration status vocabulary & per-provider configuration
├── IVR_SETUP.md               # Twilio inbound IVR setup & operations guide
├── docker-compose.yml         # PostGIS + Redis + ClamAV + migrate + backend + worker + nginx
├── Dockerfile.backend         # python:3.11-slim, non-root user, healthcheck
├── Dockerfile.frontend        # node:20 build → nginx:alpine with /api & /ws proxy
├── vercel.json / netlify.toml # SPA rewrites + cache/WASM headers for static hosting
└── .github/workflows/ci.yml   # Frontend & backend pipelines (see Testing & CI)
```

---

## Backend (FastAPI)

Async Python 3.11 service under `backend/`, mounted at `/api/v1` (legacy `/api` aliases kept for `ml`, `reports`, `animals`, `alerts`).

### API routers (18)

| Router | Responsibility |
| --- | --- |
| `auth` | Signup per role, login (email **or** phone), JWT access/refresh with rotation & reuse detection, logout, session list, gated demo login, `/me` |
| `users` | Directory, verification & activation (admin, jurisdiction-scoped) |
| `animals` | Farms, herds, animals with coordinates & tagging |
| `reports` | Disease reports with server-side triage, verification, idempotent creation |
| `cases` | Veterinary case lifecycle: dispatch offer → accept/reject → assign → status → visits |
| `labs` | Sample registration, 9-stage status flow, chain-of-custody, test entry, verification |
| `vaccinations` | Campaigns and vaccination records (dose, batch, due-date reminders) |
| `surveillance` | Overview, districts and trends — **computed from stored records only** |
| `gis` | Layers/routes built from stored records (no hardcoded clusters; OSRM or `ETA_UNAVAILABLE`) |
| `alerts` | Alert feed, mark-read, notification inbox |
| `sync` | Offline push/pull with cursors, version conflicts & resolutions |
| `voice` | Multilingual intent parsing (`/voice/intent`) and translation |
| `external` | NADRES bulletins, census, weather, data-source status, ingestion, WhatsApp & legacy IVR webhooks |
| `audit` | Tamper-evident audit log queries (restricted roles) |
| `ml` | Risk prediction, outbreak detection, forecasting, clustering, model card & performance |
| `telephony` | Twilio voice webhooks (signature-validated, fail-closed): inbound, IVR, survey, status, recording |
| `calls` | Vet-dashboard view of IVR calls: list, detail, transcript, recording, close, demo simulate |
| `callbacks` | Callback queue (Path B): list, accept, call-back, complete, convert to case |

### Domain services

- **Triage engine** (`services/triage_service.py`) — species/symptom/mortality/temperature rules with clinical red flags → risk (`LOW/MODERATE/HIGH/CRITICAL`) and urgency (`ROUTINE/URGENT/EMERGENCY`), always with explanations and a "not a diagnosis" disclaimer. Temperature accepted in °C or °F with unit validation.
- **Dispatch engine** (`services/dispatch_service.py`) — Haversine proximity over eligible `VeterinarianProfile`s, offer/accept workflow with expiry (`DISPATCH_ACCEPT_TIMEOUT_MINUTES`), availability & specialisation matching.
- **Alert engine & outbreak detection** (`services/alert_engine.py`, `services/outbreak_service.py`) — threshold + ML cluster triggers, district-scoped alert creation.
- **Lab integration** (`services/lab_integration.py`) — 9-stage sample lifecycle `COLLECTED → IN_TRANSIT → RECEIVED → ACCEPTED → TESTING → RESULT_PENDING → VERIFIED → RELEASED → CLOSED` with custody events and result revisions (no silent edits).
- **Notification service** (`services/notification_service.py`) — SMS (`fast2sms` with DLT template IDs, `dev_log`, `none`), WhatsApp Cloud API (`X-Hub-Signature-256` verified webhook), in-app alerts. `DELIVERED` is set **only** from a provider receipt.
- **File service** (`services/file_service.py`) — uploads with MIME/extension/magic-byte validation, random storage keys, ClamAV scanning (refused without a scanner in production), retention expiry, per-request authorised downloads.
- **Idempotency & rate limiting** (`services/idempotency.py`, `services/rate_limit.py`) — `Idempotency-Key` replay protection; per-IP/user limits with `memory` or `redis` backends.
- **External data service** (`services/external_data_service.py`) — NADRES, DAHD census, Open-Meteo adapters with persisted `data_source_status` and honest `LIVE / CONFIGURED / MOCK / UNAVAILABLE` states (see [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md)).
- **Translation service** (`services/translation_service.py`) — Google provider or local glossary fallback clearly labelled `FALLBACK_GLOSSARY_PARTIAL`.

### Data layer

- **37 tables** in `backend/models.py` (users, sessions, farms, herds, animals, disease reports, cases, workflow events, vet profiles, dispatch requests, visits, laboratories, facilities, lab samples + custody + tests + result revisions, vaccination campaigns/records, surveillance observations, outbreak events, alerts, notifications, audit logs, external data records, data source status, snapshots, sync events/conflicts, idempotency, jobs, call sessions/transcripts, IVR surveys/responses, callback requests, stored files).
- **Schema is managed by Alembic** (`migrations/versions/`): `0001_baseline` → `0002_postgis` (geometry columns & spatial indexes) → `0003_telephony_ivr`. CI runs upgrade → check → downgrade → upgrade against PostGIS 15.
- PostgreSQL/PostGIS in staging/production (`asyncpg`); transparent **SQLite fallback** (`aiosqlite`) for local development and tests. `create_all` is dev/test-only — production always migrates.

---

## Inbound Telephony & IVR (Twilio)

Farmers without smartphones can dial a real Twilio number. Full setup guide: [IVR_SETUP.md](IVR_SETUP.md).

```
Farmer phone ──► Twilio ──► POST /api/v1/telephony/inbound   (X-Twilio-Signature validated, fail-closed)
                                    │
                 ┌──────────────────┴───────────────────┐
       Path A: vet available                Path B: vet unavailable
       <Dial> the on-duty veterinarian      8-question DTMF survey in the caller's language
       (optional recording + status         (validate · repeat · back · cancel)
       callbacks)                                        │
                 │                              finalize_survey() → DiseaseReport (source="IVR")
                 │                                        → triage → CallbackRequest
                 └──────── one CallSession row (state machine, district-scoped) ────────┘
```

- **Languages:** `en hi mr te kn ta gu bn` (DTMF selection, `IVR_DEFAULT_LANGUAGE` fallback).
- **Recordings** (optional, `CALL_RECORDING_ENABLED`) can be transcribed via OpenAI Whisper (`STT_PROVIDER`) and summarised by OpenAI (`AI_SUMMARY_PROVIDER`) — when unconfigured the summary is an honest `NOT_CONFIGURED`; nothing is invented.
- **Every call event streams to the dashboards** over the existing WebSocket manager (`CALL_STARTED` … `CALL_COMPLETED`).
- **Mock provider** (`TELEPHONY_PROVIDER=mock`) plus `POST /api/v1/telephony/demo/simulate` (requires `DEMO_MODE`, refused in production) drive demos and the 25-test telephony suite.
- **Signature security:** every voice webhook verifies `X-Twilio-Signature` (Twilio `RequestValidator`, fail-closed); production refuses to start without it.

---

## Background Worker & Scheduled Jobs

`python -m backend.worker` executes the `jobs` table queue (PostgreSQL `SKIP LOCKED` — safe to run multiple replicas; `dedup_key` collapses duplicate schedules). In development the API can run jobs **inline** (`JOB_BACKEND=inline`); production requires the dedicated worker.

| Scheduled job | Interval | Purpose |
| --- | --- | --- |
| `dispatch.expire_offers` | 60 s | Expire unanswered vet dispatch offers |
| `health.providers` | 5 min | Refresh external provider reachability |
| `outbreak.detect` | 15 min | Run outbreak/cluster detection |
| `vaccination.reminders` | 1 h | Queue reminders for doses due within 3 days (consent-checked) |
| `ingest.nadres` / `ingest.government` | 6 h | Pull authorised external surveillance feeds |
| `cleanup.retention` / `call.cleanup_recordings` | daily | Purge expired uploads/voice recordings & idempotency keys |

Other handlers: `notification.deliver` (SMS/WhatsApp dispatch with retries).

---

## Real-Time Events (WebSocket)

- Endpoint: `ws(s)://…/api/v1/ws` (legacy `/ws` also mounted). Auth via the `Sec-WebSocket-Protocol: bearer,<token>` subprotocol or `?token=` — identity **always** comes from the verified token; client-supplied identity params are ignored. Origin checked against `CORS_ORIGINS`.
- Clients `SUBSCRIBE` to topics; delivery is filtered server-side by role, jurisdiction and ownership (`services/websocket_manager.py`).
- Standardised event catalogue in `services/events.py` — domain events (`report.*`, `case.*`, `vet.*`, `sample.*`, `lab.*`, `outbreak.*`, `alert.*`, `notification.*`, `sync.*`) plus the full IVR call lifecycle (`call.started` → `call.completed`), each carrying both a `domain.event` name and the legacy `UPPER_SNAKE` `type` for backwards compatibility.
- Frontend shows a live connection banner (`CONNECTED`, `RECONNECTING`, `OFFLINE`, `SYNCING`).

---

## Machine Learning

- **Canonical engine:** `backend/services/ml_service.py` — every ML endpoint (predict, outbreak, forecast, cluster, model card, performance) lives in the main backend. `ml-backend/main.py` is an optional thin wrapper that mounts the same router for separate deployment; there is exactly one implementation.
- **Models:** `RandomForestClassifier` (class-weighted) + `IsolationForest` for anomaly-based outbreak signals, trained by `ml-backend/train_model.py`. The shipped `model_card.json` honestly declares `training_data_type: SYNTHETIC`, `validation_status: NOT_VALIDATED_SYNTHETIC` — predictions carry insufficient-data and labels guards.
- **Offline browser fallback:** `public/model_weights.json` + `services/LocalMLService.ts` keep the AI early-warning screen working with no backend; ONNX Runtime WASM is bundled under `public/wasm/`.
- Endpoints (canonical + legacy aliases): `POST /api/v1/ml/predict`, `POST /api/v1/ml/outbreak-detection`, `POST /api/v1/ml/forecast`, `POST /api/v1/ml/cluster`, `GET /api/v1/ml/model-card`, `GET /api/v1/ml/model-performance`.

---

## Frontend (React 19 PWA)

- **Stack:** React 19, TypeScript, Vite 8, Tailwind 4, React Router 7, Recharts, Leaflet/react-leaflet, lucide-react; PWA via `vite-plugin-pwa` (Workbox precache + runtime caching for ML assets, GeoJSON, OSM tiles and `/api` responses with `NetworkFirst`).
- **Dedicated role portals:** `/login` hub and separate login/signup pages per role (`/login/farmer`, `/login/veterinary`, `/login/laboratory`, `/login/government` with aliases), plus a `/signup` hub. Each portal offers real credential login and (when the server enables it) **1-tap demo login** (`POST /api/v1/auth/demo-login/{role}`).
- **16 authenticated modules:** Dashboard, Farmer Portal, Disease Surveillance, GIS Risk Map, AI Early Warning, Case Reporting, Animal Health, Vet Response, Lab Management (dashboard, sample registration/registry/details), Vaccination Management (dashboard, campaigns, registry, record), Alerts & Notifications, Multilingual management, Offline Sync, Disease Info, Analytics, Administration.
- **Voice-first farmer experience:** `PersistentVoiceAssistant.tsx` — persistent floating mic, multi-turn Web Speech STT/TTS, server intent extraction (`/api/v1/voice/intent`) for `REPORT_DISEASE`, `REQUEST_VETERINARIAN`, `VIEW_ANIMALS`, `CHECK_VACCINATION`, `CHECK_LAB_RESULT`, `SYNC_DATA`, `GET_DISEASE_INFORMATION`; write actions require explicit voice/click confirmation and are sent with an `Idempotency-Key`.
- **Offline speech-to-text:** `workers/whisperWorker.ts` runs quantised `Xenova/whisper-tiny` ONNX fully in-browser (models under `public/models/`), enabling field voice reports with no network.
- **Maps:** `PashuMap.tsx` uses Google Maps when `VITE_GOOGLE_MAPS_API_KEY` is set and otherwise degrades to the embedded Leaflet GIS view (Maharashtra GeoJSON layers in `public/`).
- **8-language UI:** complete, key-identical dictionaries for **English, Hindi, Marathi, Telugu, Kannada, Gujarati, Tamil, Bengali** (`locales/*.ts`) with a multilingual management screen and voice-assistant support in each language.
- **API layer:** `services/apiAuth.ts` wraps every same-origin `/api/...` fetch with bearer auth, transparent refresh-token rotation on 401, and session-expiry events; the Vite dev server proxies `/api` and `/ws` to the backend (`ML_BACKEND_URL`, default `http://127.0.0.1:8000`).

---

## Offline-First Synchronisation

- All writes made offline are queued in **IndexedDB** (`services/db/IndexedDBService.ts`) and pushed via `POST /api/v1/sync/pull|push` with per-item idempotency keys and version numbers.
- The backend records `SyncEvent`s and persists genuine `SyncConflict`s (version mismatches) for explicit resolution (`GET /api/v1/sync/conflicts`, `POST /api/v1/sync/conflicts/{id}/resolve`) instead of last-write-wins data loss.
- Replayed pushes are idempotent (deduplicated server-side); the Sync screen (`/offline`) surfaces queue state, conflicts and last-sync time.

---

## Roles & RBAC

Six roles with strict, server-enforced jurisdiction (district scoping is never taken from client input):

| Role | Primary capabilities | Explicitly restricted |
| --- | --- | --- |
| **FARMER** | Voice assistant, register animals/herds, report sick animals, request vet, view vaccinations & lab results | No administrative or state-wide surveillance access |
| **VETERINARIAN** | Dispatch queue, accept/reject cases, status transitions, visits, clinical notes, order lab samples | Cannot verify lab results or change state policy |
| **LAB_TECHNICIAN** | Receive samples, custody chain, RT-PCR/ELISA test entry, result verification for surveillance release | No field veterinary triage |
| **DISTRICT_OFFICER** | District risk monitoring, containment tracking, vet workload oversight | Cannot widen own jurisdiction (server-tested) |
| **STATE_OFFICER** | State-wide surveillance, campaigns, outbreak status, NADRES comparison, GIS hotspots | — |
| **SYSTEM_ADMIN** | User verification/activation, audit investigation, configuration | Unrestricted |

Signup is role-scoped (`/api/v1/auth/signup/{farmer|vet|lab|government}`); elevated roles cannot self-escalate (tested), passwords require strength minimums, and accounts can require admin verification.

---

## Demo Accounts

There are **no hardcoded passwords anywhere** (the legacy bypass passwords were removed and are *actively rejected* by tests). Demo access is opt-in and always labelled `is_demo = true`:

1. Set in `.env`:
   ```bash
   DATA_MODE=hybrid            # or "demo" — production forces "live" and refuses demo data
   SEED_DEMO_DATA=true
   ENABLE_DEMO_LOGIN=true
   DEMO_USER_PASSWORD=YourDemoPassword123   # you choose it; never committed
   ```
2. Start the backend once (schema bootstrap seeds the demo users), or run manually:
   ```bash
   python -m backend.init_db --seed-demo
   ```

| Role | Login identifier (email or phone) | Notes |
| --- | --- | --- |
| 🌾 Farmer | `farmer.demo@pashushield.local` / `9000000001` | Demo farm, herd & animals in Pune (Shirur) |
| 👨‍⚕️ Veterinarian | `vet.demo@pashushield.local` / `9000000002` | Available profile, 40 km radius, Cattle/Buffalo |
| 🧪 Lab Technician | `lab.demo@pashushield.local` / `9000000003` | Demo diagnostic laboratory |
| 🏛️ District Officer | `district.demo@pashushield.local` / `9000000004` | Pune district scope |
| 🏛️ State Officer | `state.demo@pashushield.local` / `9000000005` | State-wide surveillance |
| 🛠️ System Admin | `admin.demo@pashushield.local` / `9000000006` | Administration & audit |

Password for all of the above = **`DEMO_USER_PASSWORD`** from your `.env`. The login portals also expose **1-tap demo login** buttons that call the gated `demo-login` endpoint (no password entry).

> `DATA_MODE=live` (required in production) refuses demo seeding and demo login outright; `DATA_MODE=hybrid` marks demo rows so they never contaminate surveillance figures.

---

## End-to-End Workflow

```
FARMER (app / voice / phone call IVR)
  │  "My cow has fever and blisters" — or — Twilio DTMF survey
  ▼
INTENT / SURVEY FINALISATION  →  DiseaseReport created (idempotent, source-tagged)
  ▼
CLINICAL TRIAGE ENGINE (rule-based, disclaimed)
  │  risk: LOW→CRITICAL · urgency: ROUTINE/URGENT/EMERGENCY
  ▼
DISPATCH ENGINE  →  proximity-ranked vets receive offers (real-time WebSocket)
  │  offer expires if unaccepted (worker job)
  ▼
VETERINARIAN ACCEPTS  →  ASSIGNED → EN_ROUTE → ON_SITE → visits recorded
  ▼
LAB SAMPLE ORDERED  →  custody chain → tests (RT-PCR/ELISA/serology) → VERIFIED
  ▼
ALERT ENGINE / OUTBREAK DETECTION  →  district-scoped alerts (worker-scheduled)
  ▼
NOTIFICATIONS  →  SMS (DLT templates) / WhatsApp (signed webhook receipts) / in-app
```

---

## Local Setup & Running

**Prerequisites:** Node.js ≥ 20.19 and npm · Python ≥ 3.11 with pip.

### 1. Backend (port 8000)

```bash
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements-dev.txt                   # backend deps + pytest + ruff

cp .env.example .env                                  # dev defaults are safe (SQLite, ephemeral JWT secrets)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- Dev defaults: SQLite (`./pashu_shield.db`), auto-created schema, ephemeral JWT secrets (a warning is logged), `docs` at `http://localhost:8000/docs`.
- Health probes: `GET /live` · `GET /ready` (DB + ML status) · `GET /health` (full detail).
- Optional demo data: see [Demo Accounts](#demo-accounts).
- Optional PostGIS: point `DATABASE_URL` at `postgresql+asyncpg://…` and run `alembic upgrade head`.

### 2. Frontend (port 5173)

```bash
npm install --ignore-scripts      # skips the optional sharp native download
npm run dev -- --host 0.0.0.0     # proxies /api and /ws to the backend
```

Open `http://localhost:5173`. With no backend running, the PWA still boots in offline mode (IndexedDB + browser ML fallback + cached GIS data).

### 3. Optional: separate ML service

```bash
PYTHONPATH=. python -m uvicorn ml-backend.main:app --port 8100   # mounts the canonical ML router
```

---

## Configuration & Environments

All configuration lives in environment variables — see [`.env.example`](.env.example) for every variable with comments. Rules enforced by `backend/config.py::validate_for_environment`:

- **No secret has a hardcoded default.** Dev/test generates ephemeral secrets with a warning; **production/staging refuse to start** without `JWT_SECRET` + `JWT_REFRESH_SECRET` (≥ 32 chars, distinct), an explicit `CORS_ORIGINS` allow-list (no `*`), PostgreSQL (`DATABASE_URL`), `JOB_BACKEND=worker`, `RATE_LIMIT_BACKEND=redis`, and `DATA_MODE=live`.
- **`ENVIRONMENT`:** `development | test | staging | production` — production disables `/docs`, enables HTTPS redirect, and rejects mock/dev adapters (`dev_log` SMS/WhatsApp, mock telephony, demo login/seeding, unscanned uploads).
- **`DATA_MODE`:** `live` (real data only) · `hybrid` (real + clearly-labelled demo rows) · `demo` (evaluation).
- **Provider selection is explicit:** SMS (`none|dev_log|fast2sms`), WhatsApp (`none|dev_log|whatsapp_cloud_api`), translation (`local|google`), routing (`none|osrm`), weather (`open_meteo|none`), labs, NADRES/government feeds, telephony (`twilio|mock`), STT/AI summary (optional OpenAI).
- Validation failures list every fatal problem at startup — the process never silently downgrades.

---

## Docker Deployment

One command brings up the full stack — **PostGIS 15 + Redis 7 + ClamAV + one-shot Alembic migration + FastAPI backend + background worker + Nginx frontend**:

```bash
cp .env.example .env        # then set at minimum:
#   POSTGRES_PASSWORD, JWT_SECRET, JWT_REFRESH_SECRET, CORS_ORIGINS
docker compose up --build -d

docker compose ps
docker compose logs -f backend worker
```

- `migrate` runs `alembic upgrade head` and must complete before backend/worker start.
- The backend image runs as a non-root user with a `/live` healthcheck; uploads persist in the `uploads` volume and are ClamAV-scanned.
- The frontend container (nginx) proxies `/api/` and `/ws` to the backend, so the browser only ever talks to one origin.

---

## Hosting (Vercel / Netlify / GitHub Pages)

The SPA ships with ready static-host configs (SPA rewrites, immutable asset caching, `sw.js` revalidation, correct `.wasm` content-type):

- **Vercel:** `vercel.json` · **Netlify:** `netlify.toml` (+ `public/_redirects`) · **GitHub Pages / sub-path:** `VITE_BASE_PATH=/Pashu-Shield/ npm run build`.
- Point `VITE_API_BASE_URL` (or a same-origin proxy) at your backend; with it empty the app uses relative `/api`.
- Twilio webhooks always target the **backend** host (`PUBLIC_API_BASE_URL`), not the static host.

---

## Testing & CI

### Backend (59 tests)

```bash
PYTHONPATH=. pytest tests -v            # API/RBAC + services + telephony suites (SQLite, temp DB)
ruff check backend tests                # lint
alembic upgrade head && alembic check   # migrations (PostGIS used in CI)
```

Suites cover: auth & refresh-token rotation/reuse detection, RBAC denial and jurisdiction-widening prevention, report→triage→case→dispatch pipeline, idempotent report submission, lab custody/verification, sync conflicts, surveillance/GIS **no-fabricated-data** guarantees, upload validation, production config rejection, and the full IVR flow (signature validation, DTMF survey, duplicate webhooks, vet bridging & fallback, recordings/transcripts RBAC, call state machine).

### Frontend

```bash
npm run typecheck      # tsc -b
npm run lint           # oxlint
npm run build          # production bundle
npm run smoke          # build + headless jsdom smoke test rendering every route (fake-indexeddb)
```

### CI (`.github/workflows/ci.yml`)

- **frontend job:** `npm ci --ignore-scripts` → typecheck → lint → build → headless route smoke test.
- **backend job:** ruff → pytest (SQLite) → Alembic upgrade/check/downgrade/upgrade on **PostGIS 15** service → production-config refusal check → secret scan (no committed `.env`, no private keys).

Manual end-to-end IVR check against a real Twilio number: `scripts/ivr_smoke.py` (see [IVR_SETUP.md](IVR_SETUP.md)).

---

## Security Posture

- **Auth:** bcrypt (configurable rounds), short-lived access tokens (15 min), rotating refresh tokens (14 d) with reuse detection, per-user sessions with server-side revocation, login attempt lockout.
- **Authorisation:** `require_roles` dependencies on every router; district/taluka jurisdiction enforced server-side; ownership-scoped downloads; farmer PII (phone) masked without permission.
- **Webhooks:** Twilio `X-Twilio-Signature` (fail-closed) and WhatsApp `X-Hub-Signature-256`; optional shared-secret header for non-provider callers.
- **Input & uploads:** Pydantic validation, request-size caps, coordinate/unit sanity checks, magic-byte file validation + ClamAV, random storage keys, retention purges.
- **Auditing:** append-only `AuditLog` for security-relevant actions, request-ID correlation (`X-Request-ID`) and structured JSON logs.
- **Rate limiting:** per-IP/user with memory (dev) or Redis (production) backends.
- **Ops hardening:** production refuses insecure starts (see [Configuration](#configuration--environments)); CI scans for committed secrets.

---

## External Integrations

Pashu-Shield never fakes external data. Each adapter reports an honest status (`LIVE / CONFIGURED / MOCK / UNAVAILABLE`) via `GET /api/v1/external/data-sources`, and the UI shows *configuration required* instead of placeholder numbers. Full matrix in [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md).

| Integration | Env vars | When unconfigured |
| --- | --- | --- |
| ICAR-NIVEDI NADRES bulletins | `NADRES_API_URL`, `NADRES_API_KEY` | No surveillance numbers shown; status `UNAVAILABLE` |
| DAHD / state surveillance feed | `GOVERNMENT_API_URL`, `GOVERNMENT_API_KEY` | Same as above |
| Weather (Open-Meteo, keyless) | `WEATHER_PROVIDER=open_meteo` | Weather factors omitted from risk context |
| Lab LIMS | `LAB_PROVIDER`, `LAB_API_URL`, `LAB_API_KEY` | Manual entry (`source=MANUAL_ENTRY`) |
| SMS (Fast2SMS + DLT templates) | `SMS_PROVIDER=fast2sms`, `SMS_API_KEY`, `SMS_DLT_TEMPLATE_IDS` | Notifications stay `PENDING`/`FAILED` |
| WhatsApp Cloud API | `WHATSAPP_PROVIDER=whatsapp_cloud_api`, token/phone-ID/app-secret | Same; webhook requires valid signature |
| Google Cloud Translation | `TRANSLATION_PROVIDER=google`, `TRANSLATION_API_KEY` | Local glossary fallback, labelled partial |
| OSRM routing | `ROUTING_PROVIDER=osrm`, `OSRM_URL` | Straight-line distance labelled; `ETA_UNAVAILABLE` |
| Twilio voice / IVR | `TWILIO_*`, `PUBLIC_API_BASE_URL`, `IVR_ENABLED` | `/api/v1/telephony/*` returns 503 |

Live status is confirmed by the worker's scheduled `ingest.*` / `health.providers` jobs (`last_success_at` on the data-sources endpoint). Institutional connections (NADRES, DAHD) additionally require official MoUs/authorisation.

---

## License & Attribution

Built for Maharashtra livestock-health operations. Bundled assets: OpenStreetMap tiles & Leaflet (BSD-2), Whisper-tiny ONNX weights (MIT), ONNX Runtime Web (MIT), Twilio SDK (MIT). Model weights shipped in `ml-backend/models/` are trained on **synthetic** data for development only — see `ml-backend/models/model_card.json`.
