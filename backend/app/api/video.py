"""Video upload & analysis API endpoints."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import get_settings
from app.core.database import get_db
from app.models import VideoJob
from app.schemas.video import (
    VideoAnalyzeResponse,
    VideoStatusResponse,
    VideoUploadResponse,
)
from app.services import video_service

router = APIRouter(prefix="/video", tags=["video"])

Db = Annotated[object, Depends(get_db)]


def _upload_response(job: VideoJob) -> VideoUploadResponse:
    return VideoUploadResponse(
        video_id=job.video_id,
        filename=job.original_filename,
        size=job.file_size,
        status="queued",
    )


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video file",
)
async def upload_video(db: Db, camera_id: str = Form(None, description="Camera this video belongs to (optional)"), file: UploadFile = File(..., description="Video file (mp4, mov, avi, mkv, webm, m4v, mpeg)")):
    """Stage a video file. Validates type & size, stores under a generated id."""
    job = await video_service.upload_video(db, file, camera_id=camera_id)
    return _upload_response(job)


@router.post(
    "/{video_id}/analyze",
    response_model=VideoAnalyzeResponse,
    summary="Start asynchronous video analysis",
)
async def analyze_video(db: Db, video_id: str, camera_id: str = Form(None, description="Camera to associate detected incidents with (optional)")):
    """Queue a video for AI analysis. Returns immediately; progress is
    available via GET /api/video/{video_id}/status."""
    if camera_id:
        video_service.assign_camera(db, video_id, camera_id)
    job = await asyncio.to_thread(video_service.start_analysis, db, video_id)
    if get_settings().background_worker:
        from app.services.job_runner import process_job_sync
        job_id = job.id
        loop = asyncio.get_running_loop()
        from app.core.runtime import runtime
        loop.run_in_executor(runtime.executor, process_job_sync, job_id, get_settings())
    return VideoAnalyzeResponse(video_id=video_id, status="processing")


@router.get(
    "/{video_id}/status",
    response_model=VideoStatusResponse,
    summary="Get video analysis status",
)
def video_status(db: Db, video_id: str):
    """Return the current status of a video analysis job."""
    job = video_service.get_status(db, video_id)
    return VideoStatusResponse(**video_service.status_response(job))