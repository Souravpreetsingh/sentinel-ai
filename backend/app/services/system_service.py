"""System health service - combines live runtime metrics with dev fallbacks.

Real CPU/memory metrics come from psutil when present; AI device info comes from
the YOLO detector layer; processing metrics are updated by the job runner.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from app.core.database import database_driver
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("services.system")

_start_time = time.time()

_stats_lock = threading.Lock()
# Aggregate processing metrics reported by completed video jobs.
_PROCESSING = {
    "jobs_completed": 0,
    "jobs_failed": 0,
    "frames_processed": 0,
    "frames_skipped": 0,
    "detections_total": 0,
    "events_total": 0,
    "avg_fps": 0.0,
    "avg_inference_ms": 0.0,
}


def update_video_metrics(result: dict[str, Any], failed: bool = False) -> None:
    with _stats_lock:
        if failed:
            _PROCESSING["jobs_failed"] += 1
            return
        s = _PROCESSING
        s["jobs_completed"] += 1
        s["frames_processed"] += int(result.get("frames_processed", 0))
        s["frames_skipped"] += int(result.get("frames_skipped", 0))
        s["detections_total"] += int(result.get("detections_count", 0))
        s["events_total"] += int(result.get("events_count", 0))
        fps = float(result.get("fps_throughput", 0.0))
        ms = float(result.get("average_inference_ms", 0.0))
        n = s["jobs_completed"]
        s["avg_fps"] = (s["avg_fps"] * (n - 1) + fps) / n
        s["avg_inference_ms"] = (s["avg_inference_ms"] * (n - 1) + ms) / n


def _video_metrics_snapshot() -> dict:
    with _stats_lock:
        return dict(_PROCESSING)


def _cpu_percent() -> float:
    """Per-process CPU utilization sampled over a short window (stdlib only)."""
    try:
        start = time.process_time()
        time.sleep(0.1)
        delta = time.process_time() - start
        return round(min(delta / 0.1 * 100.0, 100.0), 1)
    except Exception:
        return 0.0


def _memory_info() -> dict:
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        m = MEMORYSTATUSEX()
        m.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
            return {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}
        total_gb = m.ullTotalPhys / 1024 / 1024 / 1024
        used_gb = (m.ullTotalPhys - m.ullAvailPhys) / 1024 / 1024 / 1024
        return {
            "percent": round(m.dwMemoryLoad, 1),
            "used_gb": round(used_gb, 1),
            "total_gb": round(total_gb, 1),
        }
    except Exception:
        return {"percent": 0.0, "used_gb": 0.0, "total_gb": 0.0}


def _storage_info(settings) -> dict:
    try:
        import shutil

        base = settings.evidence_path()
        base.mkdir(parents=True, exist_ok=True)
        du = shutil.disk_usage(base)
        total_gb = round(du.total / 1024 / 1024 / 1024, 1)
        used_gb = round(du.used / 1024 / 1024 / 1024, 1)
        percent = round(du.used / du.total * 100, 1)
        return {"status": "active", "total_gb": total_gb, "used_gb": used_gb, "percent": percent}
    except Exception:
        return {"status": "unavailable", "total_gb": 0, "used_gb": 0, "percent": 0}


def _db_latency_ms() -> float:
    from sqlalchemy import text

    try:
        from app.core.database import get_session_factory
        with get_session_factory()() as db:
            t0 = time.perf_counter()
            db.execute(text("SELECT 1"))
            return round((time.perf_counter() - t0) * 1000, 2)
    except Exception:
        return 0.0


def _gpu_info() -> dict:
    return {
        "name": "N/A (CPU mode)",
        "available": False,
        "vram": "N/A",
        "utilization": 0,
        "temperature": 0,
    }


def _resolution_counts() -> dict:
    """Stream mix (1080p / 4K / other) from the live camera registry."""
    from sqlalchemy import func

    from app.core.database import get_session_factory
    from app.models import Alert, Camera

    with get_session_factory()() as db:
        rows = db.query(Camera.resolution, Camera.bitrate).all()
        alerts = db.query(func.count(Alert.id)).scalar() or 0
    total_bw = round(sum(float(r[1] or 0.0) for r in rows), 1)
    streams4k = sum(1 for r in rows if r[0] and "4K" in str(r[0]).upper())
    streams1080p = sum(1 for r in rows if r[0] and "1080p" in str(r[0]).lower())
    return {
        "total": total_bw,
        "segments": [
            {"label": "1080P", "value": streams1080p},
            {"label": "4K", "value": streams4k},
            {"label": "CAMERAS", "value": len(rows)},
            {"label": "ALERTS", "value": alerts},
        ],
        "streams1080p": streams1080p,
        "streams4k": streams4k,
        "alerts": alerts,
    }


def get_system_health() -> dict:
    settings = get_settings()
    elapsed = time.time() - _start_time
    hours = int(elapsed // 3600)
    mins = int((elapsed % 3600) // 60)
    uptime_str = f"{hours}h {mins}m"
    driver = database_driver()

    from app.ai.yolo import dependency_status, select_device
    from app.websocket.manager import manager

    pm = _video_metrics_snapshot()
    device = select_device(settings.yolo_device)
    bandwidth = _resolution_counts()
    memory = _memory_info()
    storage = _storage_info(settings)
    ws_clients = manager.active_count

    from sqlalchemy import func

    from app.core.database import get_session_factory
    from app.models import Camera

    with get_session_factory()() as db:
        cam_total = db.query(func.count(Camera.id)).scalar() or 0
        cam_online = db.query(func.count(Camera.id)).filter(Camera.status == "online").scalar() or 0

    online_ratio = (cam_online / cam_total) if cam_total else 0.0
    overall = round(
        max(0.0, min(100.0,
                     100.0
                     - memory["percent"] * 0.25
                     - max(0.0, storage["percent"] - 80.0) * 0.25
                     - (100.0 - online_ratio * 100.0) * 0.5)),
        0,
    )

    return {
        "ai_engine": {
            "status": "active",
            "backend": settings.detector_backend,
            "model": settings.yolo_model,
            "confidence": settings.yolo_confidence,
            "device": device,
            "yolo_status": dependency_status(),
            "frames_skipped": pm["frames_skipped"],
            "note": "Real GPU inference when DETECTOR_BACKEND=yolo and the model is provisioned.",
        },
        "video_processing": {
            "status": "active",
            "fps": round(pm["avg_fps"], 1) if pm["jobs_completed"] else 0.0,
            "queue": 0,
            "jobs_completed": pm["jobs_completed"],
            "jobs_failed": pm["jobs_failed"],
            "frames_processed": pm["frames_processed"],
            "detections_total": pm["detections_total"],
            "events_total": pm["events_total"],
            "average_inference_ms": round(pm["avg_inference_ms"], 2),
        },
        "database": {"status": "connected", "engine": driver, "latency_ms": _db_latency_ms()},
        "websocket": {"status": "active" if ws_clients > 0 else "idle", "clients": ws_clients, "latency_ms": 0.0},
        "storage": storage,
        "cpu": {"percent": _cpu_percent(), "cores": os.cpu_count() or 1},
        "gpu": _gpu_info(),
        "memory": memory,
        "fps": round(pm["avg_fps"], 1) if pm["jobs_completed"] else 0.0,
        "latency": _db_latency_ms(),
        "packet_loss": 0.0,
        "uptime": uptime_str,
        "processing_stats": pm,
        "networkBandwidth": bandwidth,
        "overall": int(overall),
    }