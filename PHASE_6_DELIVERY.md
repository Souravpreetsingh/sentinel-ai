# SENTINEL AI — Phase 6 Delivery (6A–6I)

Privacy-conscious AI CCTV intelligence platform. Phase 6 consolidates the
work-in-progress MVP into a complete watch-command workflow: a heterogeneous
52-camera city registry with GIS, watchlist matching with ANPR fault tolerance,
deduplicated real-time alerts, cross-camera vehicle tracking, unified
investigation/search, role-based access + audit, and capacity simulation up to
80,000 cameras — all driven by a single "run the demo test vehicle" workflow.

## What was built

### 6B — Heterogeneous camera registry + GIS
- 52 cameras: original 8 extended + Gujarat corridor `CAM-09..CAM-14`
  (the demo route) + 38 deterministic generated cameras across 22 districts.
- Heterogeneous by design: 10 vendor/VM5/protocol mixes (Hikvision/Milestone,
  Dahua/Genetec, Axis, Bosch BVMS, Uniview/ORBISCUDA, CP+, Hanwha…), RTSP/ONVIF/
  HLS sources, visual/thermal/PTZ/license-plate/fisheye types, 720p→4K.
- Lifecycle model `ACTIVE/DEGRADED/MAINTENANCE/OFFLINE/DISABLED` mapped to the
  legacy camera status; lat/lon, district, zone, road for GIS layers.
- `GET /api/gis/cameras|events|route/{id}|summary`, `GET /api/search/nearby`.

### 6C — Watchlist + plate normalisation + matching engine
- Watchlist CRUD (`/api/watchlists`) with vehicle/person entities.
- `normalize_plate` strips formatting only (clean reference key). OCR ambiguity
  (`O/Q→0, I/L→1, Z→2, S→5, T→7`) is applied at **match time, to both sides**,
  so imperfect ANPR still hits without corrupting stored plates.
- Decisions: `matched` (exact 0.99 / OCR-collapsed 0.94), `probable match`
  (fuzzy ≈0.72+sim·0.2), `no match`; thresholds via settings.

### 6D — Deduplicated real-time alerts
- `create_alert` dedups on `entity : camera : watchlist` within
  `alert_cooldown_seconds` (120 s default). Recurrences update tracking/history
  instead of spamming duplicates, then broadcast `alert.created` over WS.

### 6E — Cross-camera vehicle tracking
- `VehicleTrack` + `MovementEvent` with handoff across cameras. Track re-linking
  is **fault tolerant**: new reads re-link to the latest live track by exact key,
  OCR-collapsed key, then Levenshtein similarity (≥ `tracking_link_similarity`
  0.85), preferring the same watchlist entity. This keeps one physical vehicle on
  one track even when each camera reads a slightly different plate spelling.
- Movement rows are deduped on `track + camera + alert` so re-runs stay clean.

### 6F — Investigation, security, scale
- Unified search across detections/alerts/tracks/watchlist/cameras/evidence.
- Auth (stdlib HS256 JWT + PBKDF2), `require_roles` RBAC + audit log
  (`/api/auth/*`, `/api/audit`), default admin `admin@sentinel.local` /
  `admin12345`; `AUTH_REQUIRED=false` keeps the dev UI unauthenticated.
- Scale simulator (`/api/scale`) with presets up to 80,000 cameras + load curve.
- `ensure_schema()` migration: any drifted table is rebuilt on startup, then the
  idempotent seeder re-creates demo data without UNIQUE collisions.

### 6G — Frontend (React 19 / Vite, Material-3 Tailwind, no new deps)
- New pages: **Watchlists**, **Alerts**, **Investigation**, **Live Wall**.
- **City Map** upgraded to GIS layers (camera layer, lifecycle markers, alert
  layer, test-route overlay, legend, layer toggles).
- **Command Center**: KPI tiles (Watchlist Entries, Active Tracks) + **RUN DEMO
  TEST** button with result banner.
- `api.js` Phase 6 functions; `websocket.js` new event types (`WATCHLIST_CREATED`,
  `WATCHLIST_UPDATED`, `TRACKING_MOVEMENT`); `AppContext` state for watchlists,
  alerts, tracks; 12-item sidebar.

### 6H — Verification
- Backend: **118 tests / 118 passed** (`backend\: .venv\Scripts\python -m pytest -q`).
- End-to-end smoke: **30/30 checks passed** — 52 cameras, GIS layers, watchlists,
  login + RBAC, demo run (6 alerts / 6 evidence / single 6-hop track), demo
  idempotency (2nd run: 0 new), GIS route, unified search, scale run.
- Frontend: `npm run build` passes (46 modules); `npm run lint` warnings only.

## Demo the end-to-end workflow
1. Open **Command Center** → click **RUN DEMO TEST**.
2. Watch `GJ 01 AB 1234` light up: 6 alerts on the Gujarat corridor
   (`CAM-09..CAM-14`), one cross-camera track with 6 movement events, 6 evidence
   snapshots, live WS events.
3. Inspect **Alerts** (dedup), **Investigation** (search `GJ01AB1234`),
   **Live Wall**, and **City Map** route overlay.
4. Re-click **RUN DEMO TEST** — it is idempotent (0 new alerts/evidence/movements).

## Run on localhost
- Backend: `cd backend && .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Frontend (proxies `/api` + `/ws`): `npm run dev` → http://localhost:5173
- Seed data (52 cameras, watchlist, admin) is created automatically on startup.

## Key files
- `backend/app/services/`: `seed.py`, `plates.py`, `matching.py`,
  `watchlist_service.py`, `alert_service.py`, `tracking_service.py`,
  `gis_service.py`, `search_service.py`, `auth_service.py`, `audit_service.py`,
  `scale_service.py`, `demo_simulator.py`
- `backend/app/api/`: `watchlists.py`, `alerts.py`, `tracking.py`, `gis.py`,
  `search.py`, `auth.py`, `scale.py`, `demo.py`
- `backend/app/core/`: `database.py` (`ensure_schema`), `security.py`, `config.py`
- `backend/tests/test_phase6.py`
- `src/pages/`: `Watchlists.jsx`, `Alerts.jsx`, `Investigation.jsx`, `LiveWall.jsx`,
  `CommandCenter.jsx`, `CityMap.jsx`; `src/services/api.js`, `websocket.js`;
  `src/context/AppContext.jsx`