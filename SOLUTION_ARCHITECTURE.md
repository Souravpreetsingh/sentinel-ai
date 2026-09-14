# Sentinel AI — Solution Architecture

> One Intelligence Layer Across a Heterogeneous CCTV Ecosystem

## 1. Why this exists

Police CCTV estates are fragmented: vendors, formats, captions, resolutions and ownership
models differ per camera. X years of footage is watched by humans too late. Sentinel AI is a
single intelligence layer that normalises heterogeneous video into one real-time operational
picture — ANPR-matched watchlist alerts, cross-camera vehicle tracking, evidence retention
and GIS — from the edge to the state federation.

## 2. Technology stack

| Layer | Choice | Notes |
|-------|--------|-------|
| API | Python + FastAPI + Pydantic v2 | Response-model validated endpoints, OpenAPI at `/docs` |
| ORM | SQLAlchemy | SQLite (dev), PostgreSQL ready via `DATABASE_URL` (`config.is_postgres()`) |
| Realtime | Built-in WebSocket manager | Publish events via `run_coroutine_threadsafe`, auto-reconnecting client |
| Auth | JWT (PyJWT) + PBKDF2 (stdlib hashlib) | Role-gated (ADMIN/DISPOSITION/READ_ONLY), `AUTH_REQUIRED=false` in dev |
| AI | YOLO detector layer, `DETECTOR_BACKEND=mock` fallback | No heavy deps in the box; real GPU inference path is documented |
| UI | React 19 + Vite 8 + Tailwind 3 + react-router-dom | Only 3 runtime deps; Material-3 design tokens |
| Config | .env / Settings (pydantic-settings) | `VITE_API_BASE_URL` + `VITE_WS_BASE_URL` let the UI talk to the API directly |

Runtime deps are deliberately sparse — a hackathon judge can boot the whole system offline on
any Windows laptop within 60 seconds.

## 3. Logical architecture

```
            ┌───────────────────────────────  FRONTEND (localhost:5173) ───────────────────────────────┐
            │  Command Center  Live Wall  Analytics  Tracking  Evidence  GIS Map  Watchlists  System   │
            │       React 19 components · AppContext (useApp) · auto-reconnecting WS client           │
            └───────────┬──────────────────────────────────────────────┬──────────────────────────────┘
                        │ REST (http://127.0.0.1:8000/api)              │ WebSocket (ws://127.0.0.1:8000/ws/live)
            ┌───────────┴─────────────────────────────  API LAYER ──────┴─────────────────────────────┐
            │  Routers: cameras alerts watchlists tracking evidence search gis analytics scale demo   │
            │  incidents zones system audit auth video · Pydantic response models · CORS guard        │
            └──────────────────────────────┬──────────────────────────────────────────────────────────┘
                                           │
            ┌──────────────────────────────▼──────────────────  SERVICE LAYER ─────────────────────────┐
            │  demo_simulator   matching (exact/OCR/fuzzy)   tracking (fuzzy re-link, dedup)           │
            │  alert (dedup key + 120 s cooldown)  evidence (snapshot store)  seed (idempotent)        │
            │  analytics  scale (presets + load-curve)  system  camera (lifecycle reconciler)          │
            └──────────────────────────────┬──────────────────────────────────────────────────────────┘
                                           │ SQLAlchemy ORM
            ┌──────────────────────────────▼─────────────  DATA + AI  ─────────────────────────────────┐
            │  SQLite/PostgreSQL (cameras, watchlists, alerts, tracks, movements, evidence, incidents, │
            │  detections, audit) · uploads/evidence  ·  YOLO detector (mock fallback: slimmer + plate  │
            │  pre-trained path · collapse_ocr/normalize_plate matching)                                │
            └───────────────────────────────────────────────────────────────────────────────────────────┘
```

## 4. The core pipeline (what the demo proves)

```
Camera capture
   └─> 1. Detection          YOLO/mock finds vehicle + plate region (confidence per hop)
   └─> 2. ANPR normalisation normalize_plate  →  collapse_ocr (O/Q→0, I/L→1, Z→2, S→5, T→7)
   └─> 3. Watchlist match    exact 0.98+  →  OCR-collapse 0.90+  →  fuzzy/Levenshtein 0.62–0.78
   └─> 4. Alert              severity rules · dedup (entity+camera+watchlist) + 120 s cooldown
   └─> 5. Evidence           JPeg snapshot per match, linked to alert/camera
   └─> 6. Tracking           cross-camera re-link: exact → OCR-collapse → Levenshtein ≥ 0.85
                             (+0.05 same-watchlist bonus) · movement dedup (track,camera,alert)
   └─> 7. Realtime           detection / alert.created / tracking.movement pushed over WS
```

Key design decisions:

- **Matching is resilient by design.** `normalize_plate` only strips formatting and upper-cases
  (identity preserved); `collapse_ocr` maps ambiguous glyphs and is applied to *both* sides at
  match time. This is what turns `GJ0IAB1234`, `GJ01A91234` and `GJ 0L AB 1234` into one entity.
- **One alert per story, not per camera.** Dedup key `entity:camera:watchlist` + cooldown keeps
  the demo re-runnable with zero duplicates.
- **Tracking tolerates OCR drift** — the fuzzy re-linker merges hops into a single track while
  movement dedup prevents double counting.
- **Idempotent everything.** Seeders skip existing IDs; `reset_demo` wipes only dynamic artifacts;
  repeated demo runs add nothing. This is what makes the demo safe to run repeatedly for judges.

## 5. Resilience & lifecycle

- `ensure_schema()` reconciles the schema at startup (rebuilds drifted tables) so legacy/mangled
  databases self-heal.
- Camera lifecycle is a single reconciler: `lifecycle_status` (ACTIVE/OFFLINE/MAINTENANCE) maps
  to `status` (online/warning/offline) — setting a camera OFFLINE does not disturb the rest.
- WS auto-reconnect with backoff; a restarted backend re-attaches live clients automatically.
- Background worker / simulator channels toggle for deterministic tests (`BACKGROUND_WORKER=false`).

## 6. Frontend conventions

- Material-3 design tokens (surface-container, primary/secondary/tertiary, font-label-xs etc.)
- One context `AppContext` exposes `useApp()` → cameras/incidents/alerts/watchlists/tracks/health;
- Pages: Command Center, Live Wall, Analytics, Tracking, Evidence, Incidents, Watchlists,
  GIS Map, Scale, System Health, Videos, Settings.
- No external charting/state libs; zero excess weight for offline bootstrapping.

## 7. Where it scales (cross-ref)

Horizontal scaling model, per-region AI workers, gateway fan-out and the 80,000-camera
federation plan live in `SCALABILITY_80K_CAMERAS.md`; the security and compliance story is in
`CYBERSECURITY_ARCHITECTURE.md`.