"""Incident API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.database import get_db
from app.schemas.incident import (
    IncidentCreate,
    IncidentRead,
    IncidentSeverity,
    IncidentStatus,
    IncidentUpdate,
)
from app.services import incident_service

router = APIRouter(prefix="", tags=["incidents"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=list[IncidentRead], summary="List incidents")
def list_incidents(
    db: Db,
    severity: IncidentSeverity | None = Query(None, description="Filter by severity"),
    incident_status: IncidentStatus | None = Query(None, alias="status", description="Filter by status"),
    camera_id: str | None = Query(None, description="Filter by camera id"),
    limit: int = Query(200, ge=1, le=1000),
):
    """List incidents, optionally filtered by severity / status / camera."""
    return incident_service.list_incidents(
        db, severity=severity, status=incident_status, camera_id=camera_id, limit=limit
    )


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an incident",
)
def create_incident(db: Db, payload: IncidentCreate):
    """Manually create an incident record."""
    return incident_service.create_incident(db, payload)


@router.get("/{incident_id}", response_model=IncidentRead, summary="Get an incident")
def get_incident(db: Db, incident_id: str):
    """Fetch incident details by id (e.g. INC-1042)."""
    return incident_service.get_incident(db, incident_id)


@router.patch("/{incident_id}", response_model=IncidentRead, summary="Update an incident")
def update_incident(db: Db, incident_id: str, payload: IncidentUpdate):
    """Partially update an incident (status, assignment, severity, ...)."""
    return incident_service.update_incident(db, incident_id, payload)