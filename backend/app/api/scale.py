"""Scale simulation API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.scale import LoadSimPoint, ScaleResult, ScaleRunRequest
from app.services import scale_service

router = APIRouter(prefix="/scale", tags=["scale"])


@router.get("/presets", summary="Infrastructure presets")
def presets():
    return [
        {
            "name": p.name, "cameras": p.cameras, "streams_per_worker": p.streams_per_worker,
            "ai_workers": p.ai_workers, "events_per_day": p.events_per_day,
            "bandwidth_mbps": p.bandwidth_mbps, "storage_gb_per_day": p.storage_gb_per_day,
        }
        for p in scale_service.PRESETS
    ]


@router.get("/preset/{name}", summary="Expanded preset capacity plan")
def preset(name: str):
    try:
        return scale_service.preset(name)
    except ValueError:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND",
                                                     "message": f"Unknown preset '{name}'."})


@router.get("/load-curve", response_model=list[LoadSimPoint], summary="Simulated load curve")
def load_curve(cameras: int = 5000, duration_seconds: int = 60):
    return scale_service.load_curve(min(max(cameras, 50), 80000), min(max(duration_seconds, 1), 300))


@router.post("/run", response_model=ScaleResult, summary="Run capacity simulation")
def run_simulation(payload: ScaleRunRequest | None = None):
    return scale_service.run(payload)