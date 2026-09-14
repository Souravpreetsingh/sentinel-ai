# Sentinel AI — Phase 7 Demo Runbook

Competition-stage walkthrough for the Sentinel AI platform. Everything below runs against
the local development stack on a single Windows machine and every step is repeatable.

## 1. Start the stack (2 terminals)

Backend (Terminal 1):

```powershell
cd "D:\cctv ai\sentinel-ai\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend (Terminal 2):

```powershell
cd "D:\cctv ai\sentinel-ai"
npm run dev
```

Health checks:

- Backend OpenAPI: http://127.0.0.1:8000/docs
- System health: http://127.0.0.1:8000/api/system/health
- Web UI: http://localhost:5173 (logged in as `admin@sentinel.local` / `admin12345`, but
  the dev build has `AUTH_REQUIRED=false` so Read-Only demo access is guaranteed).

## 2. The 6-minute competition flow

The demo vehicle is `GJ 01 AB 1234`, a critically-watched entity (`WL-5001`) that drives the
Gujarat corridor `CAM-09 → CAM-14`. Each camera reads the plate with a different ANPR
spelling (formatting, OCR ambiguity, fuzzy substitution) proving the matching engine.

| # | Action | What the judge sees |
|---|--------|---------------------|
| 1 | Click **RESET DEMO** (Command Center) | All dynamic data wiped; readiness check shows 52 cameras + watchlist ready. Log: `demo reset complete`. |
| 2 | Click **RUN DEMO TEST** | Live feed lights up CAM-09→14 in order; 6 detections, 6 alerts, 1 cross-camera track, 6 evidence snapshots. Full pipeline finishes in ~0.5 s. |
| 3 | Open **Live Wall** on a second tab | Alerts arrive over WebSocket in real time (`alert.created`, ~570 ms after trigger). Live detection boxes + alert cards stream in. |
| 4 | Open **Command Center → Alerts** | New alerts `ALR-900x` with severities/matches; run the workflow **ACK → INVESTIGATE → RESOLVE** using the row buttons; watch `acknowledged_at` / `resolved_at` populate. |
| 5 | Open **Tracking** | Single cross-camera track `TRK-…` with 6 movement hoops and a CAD-style route; hop_count 5. |
| 6 | Open **Evidence** | 6 ANPR snapshot JPGs, downloadable, tied to alerts + cameras. |
| 7 | **Evidence of OCR resilience** | Point at the log lines: `GJ 01 AB 1234` (exact), `GJ0IAB1234` (OCR collapse), `GJ01A91234` (fuzzy 0.90), `GJ 0L AB 1234` (OCR collapse). All matched to `GJ01AB1234`. |
| 8 | Run **RUN DEMO TEST** again | Idempotent: `alerts_created: 0`, no duplicate rows, one track retained. |
| 9 | **Camera resilience** | `PATCH /api/cameras/CAM-12 {"lifecycle_status":"OFFLINE"}` → status `offline`, CAM-37 (seed) unchanged, other 50 keep producing. Restore `{"lifecycle_status":"ACTIVE"}` → `online`. |
| 10 | **Resilience flip** | Backend restart mid-demo: WebSocket client auto-reconnects (exponential backoff); ensure_schema() rebuilds any drifted table; data persists in SQLite. |
| 11 | Open **Analytics** | Overview dashboard 200 with full charts (the `_model_performance` schema fix verified via `/api/analytics/overview`). |
| 12 | Open **System Health** | Bandwidth mix segment shows 11× 4K + 28× 1080P streams, health gate `ALL SYSTEMS NOMINAL`, `overall: 98`. |

## 3. Scale slide (straight after the live demo)

Run the scale simulator at **50 / 500 / 1,000 / 10,000** cameras from the **Scale Simulator**
tab (or via `POST /api/scale/run`). The planner grows `ai_workers` (2 → 313) and gateways
(1 → 5) with flat API latency (~6.6–7.5 ms). Point to `SCALABILITY_80K_CAMERAS.md` for the
80,000-camera story and the load-curve evidence.

## 4. Reset between judging slots

```powershell
curl -X POST http://127.0.0.1:8000/api/demo/reset
```

Expected: `cleared` counters + `readiness: {cameras: 52, route_cameras_ready: true, watchlist_ready: true}`.
Run demo again and it reproduces 6 alerts / 1 track / 6 evidence; repeated runs add nothing.

## 5. Failure-free guarantees

- **Idempotent seeding**: re-running startup never duplicates cameras/watchlist/alerts/evidence
  (ID-skip seeders, `recent_deduped` pre-checks).
- **Deterministic OCR variants**: variant table is fixed per camera, so every demo run tells the
  same story.
- **SQLite dev DB** `backend/sentinel.db`; switching to PostgreSQL is a single
  `DATABASE_URL` env change (`config.is_postgres()` supported).
- **No hidden network calls**; the whole demo is self-contained offline.