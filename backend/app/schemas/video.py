"""Video upload / analysis schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

VideoJobStatus = Literal["queued", "processing", "completed", "failed"]


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str
    size: int
    status: VideoJobStatus = "queued"
    message: str = "Video staged successfully. Start analysis with POST /api/video/{video_id}/analyze"


class VideoAnalyzeResponse(BaseModel):
    video_id: str
    status: VideoJobStatus = "processing"
    message: str = "Analysis started in the background."


class VideoStatusResponse(BaseModel):
    video_id: str
    camera_id: str | None = None
    status: VideoJobStatus
    progress: float = Field(0.0, ge=0, le=100)
    error: str | None = None
    result: dict | None = None
    # --- per-job processing metrics ---
    frames_total: int = 0
    frames_processed: int = 0
    fps: float = 0.0
    detections_count: int = 0
    events_count: int = 0
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None