"""Demo endpoints — run the end-to-end Phase 6 showcase."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.services import demo_simulator

router = APIRouter(prefix="/demo", tags=["demo"])

Db = Annotated[object, Depends(get_db)]


@router.get("/status", summary="Demo configuration + readiness")
def demo_status(db: Db):
    return demo_simulator.demo_status(db)


@router.post("/reset", summary="Reset demo data to a clean, re-runnable state")
def reset_demo(db: Db):
    """Clear every artifact a previous demo run created (alerts, tracks,
    movements, demo detections, demo evidence) and re-verify the demo
    prerequisites so the demo can start clean and repeatable."""
    return demo_simulator.reset_demo(db)


@router.post("/run-test", summary="Simulate the test vehicle across the Gujarat corridor")
def run_test(db: Db):
    """Triggers a full detection→matching→alert→tracking→evidence run for the
    designated test plate (GJ 01 AB 1234). Idempotent via alert dedup."""
    try:
        return demo_simulator.run_demo_test(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"code": "DEMO_NOT_READY", "message": str(exc)})