"""Camera service layer."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import Camera
from app.schemas.camera import CameraCreate, CameraUpdate


def next_camera_id(db: Session) -> str:
    cameras = db.query(Camera.id).order_by(Camera.id.desc()).limit(1).all()
    if not cameras:
        return "CAM-01"
    nums = []
    for (cid,) in cameras:
        parts = cid.split("-", 1)
        if len(parts) == 2:
            try:
                nums.append(int(parts[1]))
            except ValueError:
                pass
    nxt = max(nums, default=0) + 1
    return f"CAM-{nxt:02d}"


def list_cameras(db: Session) -> list[Camera]:
    return db.query(Camera).order_by(Camera.id).all()


def get_camera(db: Session, camera_id: str) -> Camera:
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if cam is None:
        raise not_found("Camera", camera_id)
    return cam


def create_camera(db: Session, data: CameraCreate, camera_id: str | None = None) -> Camera:
    if data.lifecycle_status:
        lifecycle = data.lifecycle_status
        status = Camera.STATUS_FROM_LIFECYCLE.get(lifecycle, data.status)
    else:
        lifecycle = Camera.LIFECYCLE_FROM_STATUS.get(data.status, "ACTIVE")
        status = data.status
    cam = Camera(
        id=camera_id or next_camera_id(db),
        name=data.name,
        location=data.location,
        status=status,
        stream_url=data.stream_url,
        resolution=data.resolution,
        fps=data.fps,
        ai_enabled=data.ai_enabled,
        sector=data.sector,
        camera_type=data.type or "visual",
        ai_capabilities=data.ai_capabilities,
        health=data.health or 100.0,
        bitrate=data.bitrate or 0.0,
        detections=data.detections if data.detections is not None else {"people": 0, "vehicles": 0, "motorcycles": 0},
        vendor=data.vendor,
        model=data.model,
        vms_source=data.vms_source,
        protocol=data.protocol or "rtsp",
        lifecycle_status=lifecycle,
        latitude=data.latitude,
        longitude=data.longitude,
        district=data.district,
        zone=data.zone,
        road=data.road,
        firmware=data.firmware,
        capabilities=data.capabilities or data.ai_capabilities,
        error=data.error,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    _broadcast_status(cam, "camera.status_changed")
    return cam


def update_camera(db: Session, camera_id: str, data: CameraUpdate) -> Camera:
    cam = get_camera(db, camera_id)
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return cam
    prev_status = cam.status
    if "type" in update_data:
        cam.camera_type = update_data.pop("type") or cam.camera_type
    lifecycle_explicit = "lifecycle_status" in update_data
    if "lifecycle_status" in update_data:
        lifecycle = update_data.pop("lifecycle_status")
        cam.lifecycle_status = lifecycle
        cam.status = Camera.STATUS_FROM_LIFECYCLE.get(lifecycle, cam.status)
    if "status" in update_data and not lifecycle_explicit:
        cam.lifecycle_status = Camera.LIFECYCLE_FROM_STATUS.get(update_data["status"], cam.lifecycle_status)
    for field, value in update_data.items():
        if hasattr(cam, field):
            setattr(cam, field, value)
    cam.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cam)
    if cam.status != prev_status:
        _broadcast_status(cam, "camera.status_changed")
    return cam


def delete_camera(db: Session, camera_id: str) -> None:
    cam = get_camera(db, camera_id)
    db.delete(cam)
    db.commit()


def _broadcast_status(cam: Camera, event: str) -> None:
    from app.websocket import manager
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    if not loop.is_running():
        return
    try:
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(event, {
                "camera_id": cam.id,
                "camera_name": cam.name,
                "location": cam.location,
                "status": cam.status,
            }),
            loop,
        )
    except RuntimeError:
        pass