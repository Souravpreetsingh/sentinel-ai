"""Scale simulation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScalePreset(BaseModel):
    name: str
    cameras: int
    streams_per_worker: int = 16
    ai_workers: int = 8
    events_per_day: int = 50000
    bandwidth_mbps: float = 0.0
    storage_gb_per_day: float = 0.0


class ScaleRunRequest(BaseModel):
    camera_count: int = Field(500, ge=50, le=80000)
    duration_seconds: int = Field(10, ge=1, le=300)


class ScaleResult(BaseModel):
    scenario: str
    cameras: int
    ai_workers: int
    gateway_nodes: int
    streams_per_worker: int
    events_per_second: float
    api_latency_ms: float
    web_socket_latency_ms: float
    queue_throughput_per_sec: int
    worker_utilization_pct: float
    database_query_ms: float
    storage_growth_gb_per_day: float
    bandwidth_strategy: str


class LoadSimPoint(BaseModel):
    t: int
    events_per_sec: float
    api_latency_ms: float
    worker_util_pct: float
    queue_depth: int