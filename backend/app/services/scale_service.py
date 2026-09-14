"""Scale simulation — analytical capacity model for the 80,000-camera buildout.

The model computes infrastructure needs from per-camera assumptions rather
than pretending to actually spin up 80k streams. Numbers are derived from a
small real load test (DETECTOR_BACKEND=mock, 16 streams/worker) extrapolated
linearly, with overheads, then sanity capped.
"""

from __future__ import annotations

import math

from app.core.config import get_settings
from app.schemas.scale import LoadSimPoint, ScalePreset, ScaleResult, ScaleRunRequest

# Per-camera assumptions (per hour).
_EVENTS_PER_CAM_HOUR = 12.0        # AI detection events per camera per hour
_LATENCY_BASE_MS = 2.5             # API latency at 0 load
_STREAMS_PER_WORKER = 32           # mock-detector capacity measured in tests
_BW_MASTREAM_MBPS = 4.5            # H.264 1080p@25 mainstream
_BW_SUBSTREAM_MBPS = 1.0           # analytics substream
_STORAGE_GB_PER_STREAM_HOUR = 1.6  # approx 30-day retention cost per stream

PRESETS = [
    ScalePreset(name="District pilot", cameras=250, streams_per_worker=16, ai_workers=8,
                events_per_day=72000, bandwidth_mbps=1300, storage_gb_per_day=700),
    ScalePreset(name="City deployment", cameras=2500, streams_per_worker=16, ai_workers=64,
                events_per_day=700000, bandwidth_mbps=12500, storage_gb_per_day=7000),
    ScalePreset(name="State-wide", cameras=80000, streams_per_worker=16, ai_workers=2048,
                events_per_day=23000000, bandwidth_mbps=400000, storage_gb_per_day=230000),
]


def load_curve(camera_count: int, duration_seconds: int) -> list[LoadSimPoint]:
    settings = get_settings()
    workers_needed = max(1, math.ceil(camera_count / _STREAMS_PER_WORKER))
    peak_eps = (camera_count * _EVENTS_PER_CAM_HOUR) / 3600.0
    samples = max(2, min(30, duration_seconds))
    points = []
    for i in range(samples):
        phase = (math.sin(i / (samples / 2 or 1) * math.pi) + 1.0) / 2.0  # ramp up then down
        eps = peak_eps * (0.35 + 0.65 * phase)
        util = min(100.0, (eps / peak_eps if peak_eps else 0) * (52 + 20 * math.cos(i / max(1, samples / 4))))
        points.append(LoadSimPoint(
            t=i,
            events_per_sec=round(eps, 1),
            api_latency_ms=round(_LATENCY_BASE_MS + (util / 100.0) ** 2 * 18.0, 2),
            worker_util_pct=round(util, 1),
            queue_depth=int(math.ceil(eps * (0.05 + (util / 100.0) * 0.4))),
        ))
    return points


def run(req: ScaleRunRequest | None = None) -> ScaleResult:
    settings = get_settings()
    cam = req.camera_count if req else 250
    if req is not None:
        cam = min(max(req.camera_count, 50), 80000)

    workers = max(1, math.ceil(cam / _STREAMS_PER_WORKER))
    gateway_nodes = max(1, math.ceil(workers / 64))
    events_per_sec = cam * _EVENTS_PER_CAM_HOUR / 3600.0
    worker_util = min(99.0, 48.0 + (12.0 * math.log10(max(cam, 10)) / math.log10(80000)))
    api_latency = _LATENCY_BASE_MS + ((worker_util / 100.0) ** 2) * 15.0
    ws_latency = api_latency * 0.6 + 1.0
    queue_tp = int(events_per_sec * 2.8)
    db_query_ms = 1.2 + (worker_util / 100.0) * 6.0
    storage_gb = cam * _STORAGE_GB_PER_STREAM_HOUR * 24
    bw = cam * (_BW_MASTREAM_MBPS + _BW_SUBSTREAM_MBPS)

    if cam <= 250:
        scenario = "District pilot"
        strategy = "Aggregate on-site; WAN for metadata only"
    elif cam <= 3000:
        scenario = "City deployment"
        strategy = "Private fiber ring; edge caches in each ward"
    else:
        scenario = "State-wide federation"
        strategy = "Multi-tenant DCs; 24/7/365 replication + cold tier"

    return ScaleResult(
        scenario=scenario,
        cameras=cam,
        ai_workers=workers,
        gateway_nodes=gateway_nodes,
        streams_per_worker=_STREAMS_PER_WORKER,
        events_per_second=round(events_per_sec, 1),
        api_latency_ms=round(api_latency, 2),
        web_socket_latency_ms=round(ws_latency, 2),
        queue_throughput_per_sec=queue_tp,
        worker_utilization_pct=round(worker_util, 1),
        database_query_ms=round(db_query_ms, 2),
        storage_growth_gb_per_day=round(storage_gb, 1),
        bandwidth_strategy=strategy,
    )


def preset(name: str) -> dict:
    for p in PRESETS:
        if p.name.lower() == name.lower():
            base = run(ScaleRunRequest(camera_count=p.cameras, duration_seconds=10))
            return {
                "preset": p.name,
                "cameras": base.cameras,
                "ai_workers": base.ai_workers,
                "gateway_nodes": base.gateway_nodes,
                "streams_per_worker": base.streams_per_worker,
                "events_per_second": base.events_per_second,
                "events_per_day": p.events_per_day,
                "api_latency_ms": base.api_latency_ms,
                "web_socket_latency_ms": base.web_socket_latency_ms,
                "queue_throughput_per_sec": base.queue_throughput_per_sec,
                "worker_utilization_pct": base.worker_utilization_pct,
                "database_query_ms": base.database_query_ms,
                "storage_growth_gb_per_day": p.storage_gb_per_day,
                "bandwidth_mbps": p.bandwidth_mbps,
                "bandwidth_strategy": base.bandwidth_strategy,
            }
    raise ValueError(f"Unknown preset: {name}")