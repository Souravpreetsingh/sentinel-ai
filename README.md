# Sentinel AI

> **One Intelligence Layer Across a Heterogeneous CCTV Ecosystem**

Sentinel AI is a single intelligence platform that turns a fragmented city/state CCTV estate
into one real-time operational picture: **ANPR watchlist matching, cross-camera vehicle
tracking, evidence retention, GIS and analytics** — from a 50-camera district to an 80,000-camera
state federation.

## Overview

Modern CCTV estates are heterogeneous: multiple vendors, formats, resolutions, captions and
ownership models. Operators cannot watch everything — so intelligence is delivered as **events,
not pixels**. Sentinel AI normalises every feed at the edge into detections, plates, tracks and
alerts, and pushes the operational picture to a single command dashboard in real time.

## Problem

- Fragmented vendors and formats — no shared intelligence layer.
- ANPR/OCR error on dirty, angled, low-light plates breaks exact matching.
- Watchlist hits are found too late or not at all.
- No cross-camera vehicle continuity, no evidence trail, no GIS context.
- No credible path from a pilot to state-wide scale.

## Solution

- **OCR-resilient ANPR matching** (exact → OCR-collapse → fuzzy) resolves one plate, many
  readings, to one identity.
- **Real-time alerts** with dedup + cooldown, full operator workflow
  (NEW → ACKNOWLEDGED → INVESTIGATING → RESOLVED / FALSE POSITIVE).
- **Cross-camera tracking** with fuzzy re-link and movement dedup → a single vehicle story.
- **Evidence Vault** — hashed, immutable, downloadable snapshots tied to alerts/cameras.
- **Command Center, Live Wall, GIS, Analytics, System Health, Search** on one screen.
- **Horizontal scaling model** — regional gateways + distributed AI workers + event-first
  architecture (50 → 80,000 cameras).

## Technology Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy · Pydantic v2 |
| Database | SQLite (dev, zero-setup) · PostgreSQL via `DATABASE_URL` |
| Realtime | Built-in WebSocket manager + auto-reconnecting client |
| Auth | JWT (HS256, stdlib HMAC) · PBKDF2 passwords · 5-role RBAC |
| AI | YOLO detector layer with `mock` fallback (no heavy deps) |
| Frontend | React 19 · Vite 8 · Tailwind 3 · react-router-dom 6 · Material-3 tokens |
| Dev tools | oxlint · pytest · fastapi TestClient |

## Local Setup

Requirements: Windows (or any OS), Python 3.12+, Node 20+.

### Backend

```powershell
cd "D:\cctv ai\sentinel-ai\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- API + OpenAPI: http://127.0.0.1:8000/docs
- First boot seeds 52 cameras, 4 watchlist entries, incidents and evidence automatically
  (idempotent — safe to restart).

### Frontend

```powershell
cd "D:\cctv ai\sentinel-ai"
npm install
npm run dev
```

- UI: http://localhost:5173

## Demo Credentials

- **Email:** `admin@sentinel.local`
- **Password:** `admin12345`

These are **local DEMO credentials only**, pre-seeded intentionally for the hackathon build.
`AUTH_REQUIRED=false` in development also allows read-only access without a token. Never reuse
these credentials in a real deployment.

## Demo Workflow

Demo vehicle `GJ 01 AB 1234` (watchlist `WL-5001`) drives the corridor `CAM-09 → CAM-14`.

1. **Open Command Center**
2. Click **RESET DEMO** (clears prior dynamic demo data, verifies 52 cameras + watchlist readiness)
3. Click **RUN DEMO TEST** → 6 detections, 6 alerts, 1 vehicle track, 6 evidence snapshots.
4. Watch alerts stream on the **Live Wall** over WebSocket in real time.
5. Work the **Alert** status workflow, open **Evidence**, view the track + movement history,
   open **GIS** for the route, **Search** `GJ01AB1234`, check **Analytics** and
   **System Health**.

Re-running **RESET DEMO → RUN DEMO TEST** is fully idempotent — no duplicate records appear
(verified 10/10 consecutive cycles).

## 5-Minute Hackathon Demo

1. **Command Center** — 52 cameras, health/bandwidth KPIs, live feed matrix, RESET/RUN demo buttons.
2. **Camera view** — open the Live Wall or Command Center feed, click any camera, then the
   **Fullscreen** button (Esc / fullscreen button to exit; works with the demo running).
3. **RESET DEMO** → **RUN DEMO TEST** — ~0.5 s of the corridor (CAM-09 → CAM-14) producing
   6 detections, 6 alerts, 1 cross-camera track and 6 evidence snapshots.
4. **Alerts** — watch the 6 `new` alerts stream in; drive any alert through
   ACKNOWLEDGED → INVESTIGATING → RESOLVED.
5. **Evidence** — open the 6 ANPR screenshots, download one via `/api/evidence/{id}/file`.
6. **Tracking** — the single track `GJ01AB1234` with 6 movement hops (camera + time + evidence).
7. **GIS** — the vehicle's ordered route CAM-09 → CAM-14 on the map.
8. **Search** — `GJ01AB1234` returns alert/track/camera/evidence facets.
9. **Cybersecurity + scalability** — point judges at `CYBERSECURITY_ARCHITECTURE.md` and
   `SCALABILITY_80K_CAMERAS.md` (POC vs production clearly separated).

Full script with exact click order: `PHASE_8_FINAL_RUNBOOK.md`.

## API Documentation

Interactive OpenAPI docs at **http://127.0.0.1:8000/docs** (and `/redoc`). Key endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET  /api/system/health` | Live health: bandwidth 4K/1080P mix, storage, CPU/memory, WS clients, overall score |
| `POST /api/demo/run-test` | Run the ANPR corridor demo (idempotent) |
| `POST /api/demo/reset` | Reset demo data to a clean, re-runnable state |
| `GET  /api/alerts` · `PATCH /api/alerts/{id}` | Alert list + status workflow |
| `GET  /api/tracking` · `GET /api/tracking/{id}` · `GET /api/tracking/entity/{plate}` | Vehicle tracks, movements per track, entity movement history |
| `GET  /api/evidence` · `GET /api/evidence/{id}/file` | Evidence records + downloadable files |
| `GET  /api/gis/route/{plate}` | Ordered cross-camera route (CAM-09 → CAM-14) |
| `GET  /api/search?query=GJ01AB1234` | Faceted search across alerts/tracks/evidence |
| `GET  /api/analytics/overview` | Backend-derived analytics dashboard data |
| `POST /api/scale/run` `POST /api/scale/load-curve` | Horizontal-scale planner/evidence |

## Testing

```powershell
cd backend; .\.venv\Scripts\python.exe -m pytest -q     # 124 passed
npm run lint                                            # 0 errors
npm run build                                           # build PASS
```

E2E smoke checks (30/30) are documented in `HACKATHON_TEST_CASE_REPORT.md`.

## Scalability

The prototype runs **52 cameras** on one machine. The architecture is designed for horizontal
scaling and ships with a model-driven planner (`/api/scale/run`) validated at
**50 → 500 → 1,000 → 10,000 → ~80,000** cameras: regional gateways, distributed AI workers
(32 streams/worker), event-first WAN (events, not raw pixels), watchlists replicated to the edge,
and sharded storage. Measured API latency stays flat (~7 ms) as the fleet grows. The
80,000-camera story is honest: it is architecture + planner, not 80,000 live feeds on a laptop.
See `SCALABILITY_80K_CAMERAS.md`.

## Security

- HS256 JWT (stdlib HMAC) + PBKDF2 password hashing, deny-by-default RBAC (5 roles).
- Audit trail on every mutation; CORS allowlist; Pydantic-validated input/output models.
- Demo data is labeled `DEMO SIMULATION` in the UI; all shown data is representative/simulated —
  the integration layer is what consumes government feeds.
- Scope boundaries and gaps are documented honestly in `CYBERSECURITY_ARCHITECTURE.md`.

## Documentation

| Doc | Covers |
|-----|--------|
| `PHASE_8_FINAL_RUNBOOK.md` | Exact end-to-end demo commands + troubleshooting + backup plan |
| `PHASE_7_DEMO_RUNBOOK.md` | Competition judging walkthrough |
| `SOLUTION_ARCHITECTURE.md` | Stack, layers, pipeline, design decisions |
| `HACKATHON_TEST_CASE_REPORT.md` | Every measured number + reproduction commands |
| `SCALABILITY_80K_CAMERAS.md` | Tiering model, load evidence, deployment honesty |
| `CYBERSECURITY_ARCHITECTURE.md` | Auth/RBAC/audit/CORS + scope boundaries |
| `HACKATHON_PRESENTATION.md` | 15-slide deck + Q&A ammo |
| `FINAL_REPORT.md` | Hackathon readiness report |

## Limitations

- Detector runs in `mock` backend by default; real YOLO GPU inference requires provisioning.
- SQLite dev database (PostgreSQL supported via `DATABASE_URL`).
- Scale figures come from the model-driven simulator on a single machine.
- RBAC is code-enforced without external IdP; audit is SQLite rows; plate PII masking
  (IVMS governance) is a documented roadmap item.

## Future Roadmap

- Real YOLO/GPU detection path (`DETECTOR_BACKEND=yolo`), plate model weight provisioning.
- PostgreSQL + grid-region event bus (Kafka/RabbitMQ-style) for production scale.
- Object-store evidence landlines and immutable append-only audit (SIEM integration).
- External IdP (SAML/OIDC), tuned rate limiting, WAF baseline.
- Plate PII masking per IVMS data governance.
- Government-feed integration adapters on the same normalized event pipeline.