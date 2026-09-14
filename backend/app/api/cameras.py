"""Camera API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.core.errors import api_error
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services import camera_service

router = APIRouter(prefix="", tags=["cameras"])

Db = Annotated[object, Depends(get_db)]


@router.get("", response_model=list[CameraRead], summary="List all cameras")
def list_cameras(db: Db):
    """Return all registered cameras."""
    return camera_service.list_cameras(db)


@router.post(
    "",
    response_model=CameraRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new camera",
)
def create_camera(db: Db, payload: CameraCreate):
    """Create a camera. The server assigns the CAM-xx identifier."""
    return camera_service.create_camera(db, payload)


@router.get("/{camera_id}", response_model=CameraRead, summary="Get a single camera")
def get_camera(db: Db, camera_id: str):
    """Fetch camera details by id (e.g. CAM-01)."""
    return camera_service.get_camera(db, camera_id)


@router.patch("/{camera_id}", response_model=CameraRead, summary="Update a camera")
def update_camera(db: Db, camera_id: str, payload: CameraUpdate):
    """Partially update camera fields (status, resolution, ai_enabled, ...)."""
    return camera_service.update_camera(db, camera_id, payload)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a camera",
)
def delete_camera(db: Db, camera_id: str):
    """Remove a camera from the system."""
    camera_service.delete_camera(db, camera_id)