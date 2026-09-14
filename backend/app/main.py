"""SENTINEL AI - FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload
Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import asyncio
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.alerts import router as alerts_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.cameras import router as cameras_router
from app.api.demo import router as demo_router
from app.api.evidence import router as evidence_router
from app.api.gis import router as gis_router
from app.api.incidents import router as incidents_router
from app.api.scale import router as scale_router
from app.api.search import router as search_router
from app.api.system import router as system_router
from app.api.tracking import router as tracking_router
from app.api.video import router as video_router
from app.api.watchlists import router as watchlists_router
from app.core.config import get_settings
from app.core.database import get_engine, ensure_schema
from app.core.logging import configure_logging, get_logger
from app.core.runtime import runtime
from app.services import job_runner
from app.services.seed import seed_if_empty
from app.websocket.manager import manager

logger = get_logger("main")

API_TAG = "API"
NUM_CAMERAS = 52


def _parse_timestamp(value: datetime) -> str:
    return value.isoformat()


# --------------------------------------------------------------------------
# Live demo simulator - broadcasts realistic realtime events in development.
# --------------------------------------------------------------------------
async def live_simulator() -> None:
    """Broadcast detection / camera_status / system_status / analytics_update
    events to connected WebSocket clients (development only)."""
    settings = get_settings()
    counter = [0]

    def payload(event: str, data: dict) -> dict:
        return {"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        while True:
            counter[0] += 1
            i = counter[0]
            camera_id = f"CAM-{i % NUM_CAMERAS + 1:02d}"
            cam_type = ["person", "car", "motorcycle", "bicycle"][i % 4]
            obj = {
                "class_name": cam_type,
                "track_id": f"{'PERSON' if cam_type == 'person' else 'VEHICLE'} #{100 + i}",
                "confidence": round(0.78 + random.random() * 0.2, 2),
                "bbox": [random.randint(40, 500), random.randint(40, 300), random.randint(140, 600), random.randint(180, 440)],
            }
            await manager.broadcast("detection", {
                "camera_id": camera_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "objects": [obj],
            })

            if i % 4 == 0:
                await manager.broadcast("system_status", {
                    "status": "healthy",
                    "fps": round(58 + random.random() * 2, 1),
                    "latency_ms": random.randint(8, 18),
                })
            if i % 7 == 0:
                await manager.broadcast("analytics_update", {
                    "people_detected": 5721 + i,
                    "vehicles_detected": 4128 + i,
                    "events": 92 + i,
                })
            await asyncio.sleep(random.randint(6, 12))
    except asyncio.CancelledError:
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    loop = asyncio.get_running_loop()
    runtime.init(loop, worker_count=4)
    runtime.ws_manager = manager

    engine = get_engine()
    settings.ensure_dirs()

    ensure_schema(engine)

    from app.core.database import get_session_factory
    with get_session_factory()() as db:
        seed_if_empty(db)
        from app.services.auth_service import ensure_default_admin
        ensure_default_admin(db)
        requeued = 0
        from app.services.video_service import requeue_stuck
        requeued = requeue_stuck(db)
        if requeued:
            logger.info("Re-queued %d interrupted video jobs", requeued)

    tasks: list[asyncio.Task] = []
    if settings.ws_simulation:
        tasks.append(asyncio.create_task(live_simulator()))
        logger.info("WebSocket live simulator enabled (WS_SIMULATION=true)")

    if settings.background_worker:
        tasks.append(asyncio.create_task(job_runner.worker_loop(settings.worker_poll_seconds)))
        logger.info("Background job worker enabled")

    logger.info("%s backend v%s started (%s)", settings.app_name, settings.version, settings.environment)
    try:
        yield
    finally:
        job_runner.RUNNING = False
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        runtime.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SENTINEL AI API",
        description=(
            "Privacy-conscious AI-powered CCTV video analytics and incident "
            "management platform. Detection, incidents, evidence (SHA-256 "
            "hashing), analytics, video analysis and realtime WebSocket events."
        ),
        version=settings.version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(cameras_router, prefix="/api/cameras")
    app.include_router(incidents_router, prefix="/api/incidents")
    app.include_router(evidence_router, prefix="/api/evidence")
    app.include_router(analytics_router, prefix="/api/analytics")
    app.include_router(system_router, prefix="/api")
    app.include_router(video_router, prefix="/api")

    # Phase 6 — registry / intelligence / investigate / scale.
    app.include_router(watchlists_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(tracking_router, prefix="/api")
    app.include_router(gis_router, prefix="/api")
    app.include_router(search_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(scale_router, prefix="/api")
    app.include_router(demo_router, prefix="/api")

    # ------------------------------------------------------------------ root
    @app.get("/", tags=API_TAG, summary="Service information")
    def root() -> dict:
        return {
            "service": settings.service_name,
            "name": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "docs": "/docs",
            "realtime": "/ws/live",
        }

    @app.get("/health", tags=API_TAG, summary="Health check")
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.service_name,
            "version": settings.version,
        }

    # ------------------------------------------------------------- WebSocket
    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        if origin:
            from urllib.parse import urlparse

            parsed = urlparse(origin)
            allowed = (
                origin in settings.cors_origins_list
                or parsed.hostname in {"localhost", "127.0.0.1"}
            )
            if not allowed:
                await websocket.close(code=4003, reason="Origin not allowed")
                return
        await manager.connect(websocket)
        try:
            await manager.send_personal(websocket, "system_status", {
                "status": "connected",
                "service": settings.service_name,
                "version": settings.version,
            })
            while True:
                message = await websocket.receive_text()
                try:
                    import json
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await manager.send_personal(websocket, "pong", {"echo": data.get("data")})
                except Exception:
                    await manager.send_personal(websocket, "pong", {"echo": message})
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
        except Exception:
            await manager.disconnect(websocket)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level=settings.log_level.lower())