# Pashu Shield — Livestock Health Surveillance

Offline-first web application for livestock health surveillance, outbreak early warning,
laboratory sample tracking and vaccination management in Maharashtra.

* **Frontend** — React 19 + TypeScript + Vite, Tailwind CSS 4, Leaflet maps, Recharts, PWA (installable, works offline).
* **On-device AI** — disease prediction from a logistic-regression model (`public/model_weights.json`) and offline
  speech-to-text through Whisper (`@xenova/transformers`, models in `public/models/`).
* **Optional ML backend** — FastAPI service (`ml-backend/`) with a Random Forest outbreak-risk model,
  Isolation-Forest anomaly detection, forecasting and DBSCAN-style clustering.

---

## 1. Quick start

```bash
npm ci --ignore-scripts     # --ignore-scripts skips the optional sharp native download
npm run dev                 # http://localhost:5173
```

Production build and local verification:

```bash
npm run build    # type-check (tsc -b) + bundle into dist/
npm run preview  # serve dist/ locally
npm run smoke    # build, then headlessly render every route and assert key flows
```

Requirements: **Node.js ≥ 20.19** (Vite 8) and npm.

### Scripts

| Script | Purpose |
| --- | --- |
| `npm run dev` | Vite dev server with API proxy to the ML backend |
| `npm run build` | Type-check and produce the production bundle in `dist/` |
| `npm run preview` | Serve the production bundle locally |
| `npm run typecheck` | `tsc -b` only |
| `npm run lint` | oxlint |
| `npm run smoke` | Build + headless render/interaction test of all routes |

---

## 2. Optional ML backend

The **AI / Early Warning** screen talks to a FastAPI service. It is optional: if the service
is unreachable the app automatically switches to the on-device engine and clearly labels the
result as *"On-device fallback"*, so the screen never dead-ends.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r ml-backend/requirements.txt

# retrain the demo models (writes ml-backend/models/*.pkl)
python ml-backend/train_model.py

# run the API on http://127.0.0.1:8000
uvicorn main:app --app-dir ml-backend --host 0.0.0.0 --port 8000
```

Endpoints: `POST /api/predict`, `POST /api/outbreak-detection`, `POST /api/forecast`,
`POST /api/cluster`, `GET /api/model-performance`.

During `npm run dev`, requests to `/api/*` are proxied to `ML_BACKEND_URL`
(default `http://127.0.0.1:8000`), so no CORS setup is needed locally.

---

## 3. Configuration

| Variable | Scope | Default | Meaning |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | build time | `/api` | Absolute or relative base URL of the FastAPI service |
| `VITE_BASE_PATH` | build time | `/` | Sub-path the app is hosted under (e.g. `/Pashu-Shield/`) |
| `ML_BACKEND_URL` | dev/preview only | `http://127.0.0.1:8000` | Proxy target for `/api` |

Copy `.env.example` to `.env.local` to override locally. In production, a reverse proxy that
forwards `/api/*` to the FastAPI service keeps the frontend on a single origin
(recommended — no CORS, no mixed content).

```nginx
# nginx: SPA + ML service behind one origin
location /api/ { proxy_pass http://127.0.0.1:8000/api/; }
location / {
  root /var/www/pashu-shield;
  try_files $uri $uri/ /index.html;   # client-side routing
}
```

---

## 4. Deployment

The app is a static SPA. Build it and serve `dist/`.

| Platform | Setup |
| --- | --- |
| **Vercel** | Auto-detected via `vercel.json` (build `npm run build`, output `dist`, SPA rewrite, asset caching) |
| **Netlify** | Auto-detected via `netlify.toml`; `public/_redirects` covers static uploads |
| **GitHub Pages** | `VITE_BASE_PATH=/<repo>/ npm run build`, then publish `dist/` (also copy `dist/index.html` to `dist/404.html` for deep links) |
| **Static server / CDN** | Serve `dist/` and rewrite unknown paths to `index.html`; keep `sw.js` and `manifest.webmanifest` revalidation-friendly |

Two build facts matter for hosting:

1. **Deep links** (`/gis`, `/analytics`, …) must fall back to `index.html`, otherwise a refresh returns 404.
2. `dist/` is ~85 MB because the offline ML assets ship with it (`public/models/` 44 MB Whisper ONNX,
   `public/wasm/` 37 MB onnxruntime WASM). The service worker caches them on first use and does not
   precache files above 10 MB, so they never block first paint. Omit `public/models`/`public/wasm` from a
   build if offline voice transcription is not required.

---

## 5. Offline behaviour

* **Storage** — IndexedDB (`services/db/IndexedDBService.ts`), with automatic in-memory fallback when
  IndexedDB is unavailable (private browsing, blocked storage, quota errors).
* **Case reports** — drafts and the offline queue are kept in `localStorage`, validated on read, and
  flushed automatically when the browser comes back online.
* **AI** — risk scoring falls back to the bundled model; the AI screen labels the source of every result.
* **Assets** — the service worker precaches the app shell and caches ML models, district data and map
  tiles at runtime for later offline use.

If `localStorage`/IndexedDB were cleared or corrupted, the app self-heals: unreadable queues and drafts
are discarded instead of breaking the screen.

---

## 6. Project layout

```
App.tsx                  routes (each screen wrapped in an error boundary)
components/              Layout, Sidebar, Topbar, ErrorBoundary
context/                 app-wide state (reports, alerts, animals, labs, vaccination, i18n)
locales/                 English + Marathi UI strings
pages/                   one folder per feature screen
services/                API clients, ML fallback engine, offline storage, helpers
workers/whisperWorker.ts offline speech-to-text worker
public/                  PWA icons, bundled ML models + WASM, GIS reference data
ml-backend/              FastAPI service, training script and model artefacts
scripts/smoke.mjs        headless route/interaction smoke test
```

---

## 7. Testing

```bash
npm run typecheck   # TypeScript project references, strict mode
npm run lint        # oxlint — 0 warnings/errors expected
npm run smoke       # renders every route in jsdom + exercises the offline AI and report flows
```

The smoke test fails the build if any route throws, if the AI screen cannot produce a
prediction without a backend, or if a submitted case report does not appear under *My Reports*.

---

## 8. Reference data (published datasets)

The app's reference data comes from published government sources, consolidated in
`services/ReferenceData.ts` (and `public/maharashtra_locations.json` for map locations):

| Dataset | Source |
| --- | --- |
| Species populations (India + Maharashtra) | 20th Livestock Census 2019, DAHD, Govt. of India |
| Districts (all 36, HQ coordinates, divisions) | Revenue & Forest Department, Govt. of Maharashtra |
| Indigenous breeds (Gir, Dangi, Deoni, Khillari, Pandharpuri, Osmanabadi, …) | ICAR-NBAGR National Register of Indigenous Livestock Breeds |
| Disease catalog (FMD, LSD, PPR, Brucellosis, HS, BQ, Anthrax, Rabies, …) | DAHD "Livestock Health & Disease Control" reports; WOAH listed-disease framework |
| Vaccination schedule & campaign targets | NADCP (six-monthly FMD dosing; one-time Brucellosis dose for 4–8-month female bovine calves; PPR eradication by 2030) |

Outbreak *counts* on the Analytics screen are still simulated (no official case-level time
series is published), but their denominators, district list and vaccination targets are
derived from the datasets above. Sample records (seeded animals/cases/samples) are labelled
as such in code until a live backend is connected.
