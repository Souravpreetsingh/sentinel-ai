"""System API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.system import SystemHealth
from app.services import system_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=SystemHealth, summary="System health status")
def system_health() -> dict:
    """Return health metrics for AI engine, video processing, DB, WebSocket,
    storage, CPU, GPU, memory, latency and uptime."""
    return system_service.get_system_health()