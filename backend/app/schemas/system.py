"""System health schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SystemHealth(BaseModel):
    ai_engine: dict = Field(default_factory=dict)
    video_processing: dict = Field(default_factory=dict)
    database: dict = Field(default_factory=dict)
    websocket: dict = Field(default_factory=dict)
    storage: dict = Field(default_factory=dict)
    cpu: dict = Field(default_factory=dict)
    gpu: dict = Field(default_factory=dict)
    memory: dict = Field(default_factory=dict)

    fps: float = 0.0
    latency: float = 0.0
    packet_loss: float = 0.0
    uptime: str = "—"

    networkBandwidth: dict = Field(default_factory=dict)
    overall: int = 0