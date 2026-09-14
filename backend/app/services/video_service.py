"""Video job service layer - upload, status, and analysis trigger."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import not_found, validation_error
from app.core.logging import get_logger
from app.models import VideoJob
from app.schemas.video import VideoJobStatus
from app.services.hashing import sha256_file

logger = get_logger("services.video")


def next_video_id(db: Session) -> str:
    return uuid.uuid4().hex


def get_video_job(db: Session, video_id: str) -> VideoJob:
    job = db.query(VideoJob).filter(VideoJob.video_id == video_id).first()
    if job is None:
        raise not_found("VideoJob", video_id)
    return job


def list_jobs(db: Session, status: VideoJobStatus | None = None, limit: int = 100) -> list[VideoJob]:
    q = db.query(VideoJob)
    if status:
        q = q.filter(VideoJob.status == status)
    return q.order_by(VideoJob.created_at.desc()).limit(limit).all()


async def upload_video(
    db: Session,
    file: UploadFile,
    settings: Settings | None = None,
    camera_id: str | None = None,
) -> VideoJob:
    settings = settings or get_settings()
    settings.ensure_dirs()

    if not file.filename:
        raise validation_error("Missing filename in upload.")

    from app.core.security import extract_extension
    ext = extract_extension(file.filename)
    if ext not in settings.allowed_video_extensions_list:
        raise validation_error(
            f"File extension '.{ext}' is not allowed. "
            f"Allowed: {', '.join(settings.allowed_video_extensions_list)}"
        )

    video_id = next_video_id(db)
    stored_name = f"{video_id}.{ext}"
    dest = settings.videos_path() / stored_name

    total = 0
    too_large = False
    with open(dest, "wb") as out:
        while True:
            chunk = await file.read(1024 * 256)
            if not chunk:
                break
            total += len(chunk)
            if total > settings.max_upload_size_bytes:
                too_large = True
                break
            out.write(chunk)

    if too_large:
        dest.unlink(missing_ok=True)
        raise validation_error(f"File exceeds {settings.max_upload_size_mb} MB limit.")

    file_hash = sha256_file(dest)

    job = VideoJob(
        id=uuid.uuid4().hex,
        video_id=video_id,
        original_filename=file.filename,
        stored_path=str(dest),
        file_size=total,
        file_hash=file_hash,
        status="queued",
        camera_id=camera_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Video uploaded: video_id=%s size=%d bytes", video_id, total)
    return job


def start_analysis(db: Session, video_id: str) -> VideoJob:
    job = get_video_job(db, video_id)
    if job.status not in ("queued", "failed"):
        return job
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.error = None
    db.commit()
    db.refresh(job)
    return job


def assign_camera(db: Session, video_id: str, camera_id: str) -> None:
    job = get_video_job(db, video_id)
    job.camera_id = camera_id
    db.commit()


def get_status(db: Session, video_id: str) -> VideoJob:
    return get_video_job(db, video_id)


def status_response(job: VideoJob) -> dict:
    return {
        "video_id": job.video_id,
        "camera_id": job.camera_id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "result": job.result,
        "frames_total": job.frames_total,
        "frames_processed": job.frames_processed,
        "fps": job.fps,
        "detections_count": job.detections_count,
        "events_count": job.events_count,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }


def requeue_stuck(db: Session) -> int:
    stuck = db.query(VideoJob).filter(
        VideoJob.status.in_(["processing", "queued"]),
    ).all()
    count = 0
    for job in stuck:
        if job.status == "processing":
            job.status = "queued"
            job.started_at = None
            count += 1
    db.commit()
    return count