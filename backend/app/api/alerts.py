"""Alert API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.schemas.alert import AlertRead, AlertUpdate
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=list[AlertRead], summary="List alerts")
def list_alerts(
    db: Db,
    status: str | None = None,
    severity: str | None = None,
    camera_id: str | None = None,
    watchlist_id: str | None = None,
    tracking_id: str | None = None,
    since: datetime | None = None,
    limit: int = 200,
):
    """List alerts with optional filters. Ordered newest-first."""
    return alert_service.list_alerts(db, status=status, severity=severity, camera_id=camera_id,
                                     watchlist_id=watchlist_id, tracking_id=tracking_id,
                                     since=since, limit=limit)


@router.get("/{alert_id}", response_model=AlertRead, summary="Get an alert")
def get_alert(db: Db, alert_id: str):
    return alert_service.get_alert(db, alert_id)


@router.patch("/{alert_id}", response_model=AlertRead, summary="Update an alert")
def update_alert(db: Db, alert_id: str, payload: AlertUpdate):
    """Acknowledge / assign / resolve alerts. Status transitions set timestamps."""
    return alert_service.update_alert(db, alert_id, payload)