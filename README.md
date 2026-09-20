# Pashu-Shield — Production Real-Time Livestock Health Surveillance & Veterinary Response Platform

**Pashu-Shield** is a full-stack, real-time, offline-first livestock disease surveillance, outbreak early-warning, and emergency veterinary response platform designed for Maharashtra state animal husbandry operations.

---

## Architecture Overview

```
                                      +---------------------------------------------+
                                      |            Pashu-Shield Frontend            |
                                      | (React 19 + TypeScript + Vite + Tailwind 4) |
                                      +---------------------------------------------+
                                        /                  |                      \
                     Role Dashboards   /                   |                       \   Accessibility
            +-------------------------+                    |                        +---------------------------+
            | 🌾 Farmer Portal        |                    |                        | 🎙️ Multi-turn Voice Assist|
            | 👨‍⚕️ Veterinarian Queue   |                    |                        | 🌐 8 Language Dictionaries |
            | 🧪 Laboratory Sample QR |                    |                        | 🗺️ Google Maps + Leaflet  |
            | 🏛️ Government Surveillance|                   |                        | 📱 Offline IndexedDB PWA  |
            +-------------------------+                    |                        +---------------------------+
                                                           |
                                                  WebSocket & REST APIs
                                                           |
                                      +---------------------------------------------+
                                      |            FastAPI Backend Service          |
                                      |       (Python 3.11 + Async Architecture)    |
                                      +---------------------------------------------+
                                        /         |             |          \       \
       Authentication & RBAC           /          |             |           \       \  External Adapters
+------------------------------------+            |             |            \       +----------------------+
| JWT Tokens + Bcrypt Hashing        |            |             |             \      | ICAR-NIVEDI NADRES   |
| 6 User Roles + Strict Jurisdiction |            |             |              \     | DAHD Livestock Census|
| Real-time Audit Logging            |            |             |               \    | Open-Meteo Weather   |
+------------------------------------+            |             |                \   | SMS (Fast2SMS/Mock)  |
                                                  |             |                 \  | WhatsApp Cloud API   |
                                       Database Layer           |                  \ +----------------------+
            +-------------------------------------------+  Realtime Event Bus       \
            | Primary: PostgreSQL 15 + PostGIS (Spatial)|  (WebSockets + Pub/Sub)    \ Clinical Triage Engine
            | Local Dev Fallback: SQLite via aiosqlite  |                             +----------------------+
            | Normalized Schemas: 18 relational tables  |                             | Rule-based Safety    |
            | SQL DDL: migrations/001_initial_schema.sql|                             | Scikit-Learn ML RF   |
            +-------------------------------------------+                             | Outbreak IsoForest   |
                                                                                      +----------------------+
```

---

## 1. What Was Implemented

1. **Complete FastAPI Production Backend (`backend/`)**:
   - `backend/config.py`: Centralized environment configuration and security settings.
   - `backend/database.py`: Async SQLAlchemy 2.0 engine with PostgreSQL/PostGIS support and transparent local SQLite fallback.
   - `backend/models.py`: 18 normalized relational models (Users, UserSessions, Farms, Herds, Animals, DiseaseReports, VeterinaryCases, VeterinaryVisits, Laboratories, LabSamples, LabTests, VaccinationCampaigns, VaccinationRecords, OutbreakEvents, Alerts, Notifications, AuditLogs, ExternalDataRecords, SyncEvents).
   - `backend/schemas.py`: Comprehensive Pydantic v2 validation models.
   - `backend/security.py`: Direct bcrypt hashing (no passlib wrap bugs), JWT access & refresh tokens, strict role-based authorization dependencies (`require_roles`).
   - `backend/init_db.py`: Complete database seeder with realistic Maharashtra districts, veterinarians, diagnostic laboratories, dairy farms, and registered herds.
   - `migrations/001_initial_schema.sql`: Production PostgreSQL + PostGIS DDL schema with spatial geometry columns and performance indexes.

2. **Real-Time Multi-User Synchronization & WebSockets**:
   - `backend/services/websocket_manager.py`: Topic-based and user-directed WebSocket connection manager (`/api/v1/ws`).
   - Real-time broadcasts for `REPORT_CREATED`, `CASE_CREATED`, `CASE_STATUS_CHANGED`, `LAB_SAMPLE_COLLECTED`, `LAB_RESULT_VERIFIED`, and `SYNC_COMPLETED`.
   - Visual WebSocket connection state banner on frontend (`CONNECTED`, `RECONNECTING`, `OFFLINE`, `SYNCING`).

3. **Safe Clinical Triage & Automated Dispatch Engine**:
   - `backend/services/triage_service.py`: Evaluates species, symptoms, mortality, body temperature, and clinical red flags without claiming certainty of diagnosis.
   - Provides risk levels (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`), urgency ratings (`ROUTINE`, `URGENT`, `EMERGENCY`), biosecurity protocols, and disclaimers.
   - `backend/services/dispatch_service.py`: Calculates Haversine distances between farmers and registered veterinarians in the district, automatically creating and routing cases to eligible veterinarians.

4. **Laboratory Sample Lifecycle & Verification**:
   - Full 9-stage lifecycle: `COLLECTED` -> `IN_TRANSIT` -> `RECEIVED` -> `ACCEPTED` -> `TESTING` -> `RESULT_PENDING` -> `VERIFIED` -> `RELEASED` -> `CLOSED`.
   - Sample QR generation, test entry (RT-PCR, ELISA, Serology), and formal verification with audit logging.

5. **Voice-First Farmer Experience**:
   - `components/PersistentVoiceAssistant.tsx`: Large persistent floating voice button (🎙️).
   - Multi-turn conversational state machine with Web Speech STT and Text-To-Speech audio feedback.
   - Extracts intent (`REPORT_DISEASE`, `REQUEST_VETERINARIAN`, `VIEW_ANIMALS`, `CHECK_VACCINATION`, `CHECK_LAB_RESULT`, `SYNC_DATA`, `GET_DISEASE_INFORMATION`).
   - Protects write actions with user voice/click confirmation.

6. **Complete 8-Language Localization Dictionaries**:
   - Complete identical keys for:
     1. `en` (English)
     2. `mr` (Marathi)
     3. `hi` (Hindi)
     4. `te` (Telugu)
     5. `kn` (Kannada)
     6. `gu` (Gujarati)
     7. `ta` (Tamil)
     8. `bn` (Bengali)
   - `TranslationService` abstraction with Google Cloud Translation provider and verified veterinary terminology glossary fallback.

7. **Production Maps with Google Maps + Leaflet Fallback**:
   - `components/PashuMap.tsx`: Detects `VITE_GOOGLE_MAPS_API_KEY`. When configured, loads Google Maps JavaScript SDK with custom markers, clustering, and route navigation. Automatically degrades to Leaflet GIS when offline or key is unconfigured.

8. **Notification Provider Architecture**:
   - `backend/services/notification_service.py`: Multi-channel provider for SMS (Fast2SMS / Twilio / Mock adapter), WhatsApp Business Cloud API, and in-app alerts.

9. **External Data Provider Layer**:
   - `backend/services/external_data_service.py`: Official adapters for ICAR-NIVEDI NADRES monthly disease forewarning bulletins, DAHD 20th Livestock Census, and Open-Meteo weather parameters.

10. **Offline-First Synchronization**:
    - Idempotency key tracking in sync queue prevents duplicate records on reconnection.
    - POST `/api/v1/sync/push` and GET `/api/v1/sync/pull` synchronize IndexedDB with primary SQL storage.

---

## 2. Existing Features Preserved

- Preserved disease reference catalog (`services/DiseaseService.ts`).
- Preserved 20th Livestock Census baseline populations (`services/ReferenceData.ts`).
- Preserved offline IndexedDB storage architecture (`services/db/IndexedDBService.ts`).
- Preserved Whisper WebAssembly worker integration for offline transcription (`workers/whisperWorker.ts`).
- Preserved machine learning models (`ml-backend/models/rf_model.pkl`, `iso_model.pkl`, `scaler.pkl`, `metrics.json`).
- Preserved PWA offline caching service worker configuration (`vite.config.ts`).
- Preserved existing GIS GeoJSON layers (`public/maharashtra_locations.json`, `public/maharashtra_state.geojson`).

---

## 3. User Roles & RBAC Matrix

| Role | Default Demo Account | Primary Capabilities | Restricted Capabilities |
| --- | --- | --- | --- |
| **FARMER** | `farmer@pashushield.gov.in` | Voice assistant, register cattle/herds, report sick animal, request vet, view vaccinations & lab results | No administrative controls, no state-wide surveillance oversight |
| **VETERINARIAN** | `vet@pashushield.gov.in` | Assigned cases queue, emergency response, on-site visit recording, clinical diagnosis, order lab samples | Cannot approve lab verification or change state policy |
| **LAB_TECHNICIAN** | `lab@pashushield.gov.in` | Receive samples, QR scan, execute RT-PCR/ELISA tests, record values, verify results for surveillance release | Cannot perform field veterinary triage |
| **DISTRICT_OFFICER** | `district@pashushield.gov.in` | District risk monitoring, outbreak containment tracking, veterinary workload oversight | Limited to district jurisdiction |
| **STATE_OFFICER** | `state@pashushield.gov.in` | Full Maharashtra surveillance, NADRES comparison, vaccination campaign management | State jurisdiction |
| **SYSTEM_ADMIN** | `admin@pashushield.gov.in` | User account approvals, role permissions, audit log investigation, system configuration | Unrestricted |

---

## 4. Critical End-to-End Workflow

```
FARMER
  │  (Speaks: "My cow has fever and blisters")
  ▼
VOICE ASSISTANT (NLP Intent Extraction)
  │  (Entities: Cattle, Fever, Blisters → Triage Urgency: EMERGENCY)
  ▼
CLINICAL TRIAGE ENGINE
  │  (Evaluates clinical red flags, assigns HIGH/CRITICAL risk)
  ▼
DATABASE RECORD CREATED (Report #MH-PUN-260901-A101)
  │  (Triggers real-time event & alerts)
  ▼
VETERINARY DISPATCH ENGINE
  │  (Calculates proximity, selects Dr. Sunita Deshmukh)
  ▼
REAL-TIME WEBSOCKET BROADCAST
  │  (Notifies Veterinarian & updates Government Surveillance)
  ▼
VETERINARIAN ACCEPTS CASE
  │  (Status: ASSIGNED → EN_ROUTE → ON_SITE)
  ▼
DIAGNOSTIC SAMPLE ORDERED
  │  (Sample #SMP-PUN-2609-10231 registered with QR)
  ▼
LABORATORY TESTING & VERIFICATION
  │  (RT-PCR confirmed → Lab Officer signs off)
  ▼
NOTIFICATIONS DISPATCHED
  │  (Farmer notified via SMS/WhatsApp; Government outbreak status updated)
```

---

## 5. Local Setup & Running Instructions

### Prerequisites
- Node.js ≥ 20.19 and npm
- Python ≥ 3.11 with pip

### Quick Start (Dev Environment)

1. **Install Frontend Dependencies**:
```bash
npm install --ignore-scripts
```

2. **Install Backend Dependencies**:
```bash
pip install fastapi uvicorn pydantic scikit-learn pandas numpy joblib sqlalchemy aiosqlite python-jose[cryptography] bcrypt websockets httpx python-multipart email-validator
```

3. **Start the FastAPI Backend Service (Port 8000)**:
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

4. **Start the Vite Frontend (Port 5173)**:
```bash
npm run dev -- --host 0.0.0.0
```

Access the application in your browser at `http://localhost:5173`.

---

## 6. Docker Deployment

Deploy the full stack (PostgreSQL + PostGIS, Redis, FastAPI Backend, Background Worker, and Nginx Frontend) with one command:

```bash
docker-compose up --build -d
```

### Checking Services
```bash
docker-compose ps
docker-compose logs -f backend
```

---

## 7. Running Tests

### Backend Automated Test Suite
```bash
PYTHONPATH=. pytest tests/test_backend.py -v
```

### Frontend TypeScript Verification & Smoke Suite
```bash
npm run typecheck
npm run smoke
```

---

## 8. External API Credentials & Legal Requirements

The following integrations use standard provider abstractions. In sandbox and development modes, high-fidelity mock adapters provide realistic behaviors. Live institutional connections require official credentials:

1. **ICAR-NIVEDI NADRES**:
   - Requires institutional memorandum of understanding (MoU) with ICAR-NIVEDI for live API endpoints.
   - Configured via `NADRES_API_KEY` and `NADRES_API_URL`.
   - Development mode serves published monthly bulletin baselines clearly marked as `HISTORICAL / PUBLISHED BASELINE`.

2. **DAHD Livestock Census & Surveillance**:
   - Official national reporting systems require Department of Animal Husbandry & Dairying authorization.
   - Configured via `GOVERNMENT_API_KEY` and `GOVERNMENT_API_URL`.

3. **Google Maps API**:
   - Requires Google Cloud console account with Maps JavaScript API enabled.
   - Configured via `VITE_GOOGLE_MAPS_API_KEY`.
   - When unset, Pashu-Shield automatically falls back to the embedded Leaflet GIS map.

4. **SMS & WhatsApp Business Cloud API**:
   - SMS requires DLT registration (Govt. of India) and a provider API key (`SMS_API_KEY`).
   - WhatsApp requires Meta Business Manager verification (`WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`).
