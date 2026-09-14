# SENTINEL AI — Backend

Privacy-conscious AI-powered CCTV video analytics and incident management platform.

- **Frontend:** React + Vite (see `../sentinel-ai`)
- **Backend:** Python + FastAPI
- **AI:** YOLO (Ultralytics) + OpenCV (+ tracking / zone / event rules)
- **Database:** PostgreSQL (SQLite development fallback)
- **Realtime:** WebSocket

---

## Quick start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt   # core backend
pip install -r requirements-ai.txt  # optional: real YOLO detection
pip install -r requirements-dev.txt # optional: tests
```

### Environment setup

```bash
cp .env.example .env
# edit .env to taste (database URL, thresholds, CORS origins, ...)
```

### Database setup

- **PostgreSQL (recommended):** set `DATABASE_URL` in `.env`, e.g.
  `postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel`.
- **SQLite fallback:** leave `DATABASE_URL` empty. Tables are created
  automatically; `sentinel.db` appears in `backend/`.

Tables, seed data (8 demo cameras, incidents, evidence) and directory creation
happen automatically at server startup.

### Server startup

```bash
uvicorn app.main:app --reload --port 8000
# or
python -m app
```

### API documentation

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/health>

CORS is enabled for the Vite dev origins (`http://localhost:5173`).

---

## API overview

| Endpoint | Purpose |
|---|---|
| `GET /health` | service health |
| `GET/POST /api/cameras`, `GET/PATCH/DELETE /api/cameras/{id}` | camera CRUD |
| `GET/POST /api/incidents`, `GET/PATCH /api/incidents/{id}` | incident CRUD + filters |
| `GET/POST /api/evidence`, `GET/PATCH /api/evidence/{id}` | evidence upload + SHA-256 hashing |
| `GET /api/analytics/{overview,events,traffic,cameras}` | analytics dashboard data |
| `GET /api/system/health` | system metrics |
| `POST /api/video/upload` | stage a video |
| `POST /api/video/{id}/analyze` | start async analysis |
| `GET /api/video/{id}/status` | job status (`queued|processing|completed|failed`) |
| `WS /ws/live` | realtime events |

### Realtime WebSocket events

`/ws/live` broadcasts `{"event": ..., "data": ..., "timestamp": ...}`:

- `detection` — object detections per camera
- `camera.status_changed` — camera status transitions
- `incident.created` / `incident.updated`
- `system_status` — health beacons
- `analytics_update` — periodic metric refreshes
- `video_job_update` — analysis job progress

---

## Video processing

> Long video analysis **never** runs inside an HTTP request — jobs are processed
> by a background worker pool.

1. `POST /api/video/upload` — validates type/size/filename, stores under a UUID
   name, returns `video_id`.
2. `POST /api/video/{video_id}/analyze` — returns immediately with
   `{"video_id": ..., "status": "processing"}`.
3. `GET /api/video/{video_id}/status` — poll for progress/result.

Pipeline: `Video → Frame → Detection → Tracking → Zone analysis → Event engine
→ Incident → WebSocket`.

```bash
# Health check for the YOLO stack (installed? model present?):
python -m app.ai.yolo --check
```

### YOLO setup

- Install AI deps: `pip install -r requirements-ai.txt`.
- Provide weights (e.g. `yolo11n.pt`) in the backend root (never auto-downloaded).
- Set `DETECTOR_BACKEND=yolo` (or keep `auto`).
- If YOLO is unavailable the server logs a clear message and falls back to the
  deterministic mock detector.

### Object classes

`person`, `car`, `motorcycle`, `bus`, `truck`, `bicycle` — COCO/YOLO outputs
are normalised into these internal names.

### Behavior rules

- Crowd density (configurable: LOW ≤ 15, MEDIUM ≤ 30, HIGH 31+) → `crowd_density_high`
- Stationary matching object without a nearby person → `abandoned_object`
- Stationary vehicle → `vehicle_stopped`
- Upright → lying aspect change → `person_fallen` (heuristic, not medical)
- Polygonal zones → `restricted_zone_entry` (presence only, no identity)
- (Accident / congestion rules are stubs ready for custom logic.)

---

## Testing

```bash
pytest -v
pytest --cov=app --cov-report=term-missing
```

Covers health, camera/incident APIs, evidence SHA-256 hashing, upload
validation, event generation, zone detection and WebSocket connectivity.

## Project layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, lifespan, WebSocket
│   ├── api/                    # HTTP routers
│   ├── ai/                     # detector, yolo, mock, tracker, zones, events
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # business logic + seed data + job runner
│   ├── websocket/              # connection manager
│   └── core/                   # config, database, logging, security
├── uploads/                    # evidence storage (auto-created)
├── videos/                     # uploaded videos (auto-created)
├── tests/
├── requirements*.txt
├── .env.example
└── README.md
```

## Security notes

- No secrets in source; everything comes from the environment.
- Evidence files are stored under server-generated names and SHA-256 hashed;
  they are never modified after hashing.
- Uploads are validated by extension, size limit and safe filenames.
- The platform performs no facial recognition, no identity matching, no
  predictive policing, and never classifies people by race, religion,
  ethnicity, emotion or other sensitive traits.