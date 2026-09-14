"""Development seed data.

Creates the Phase 6 heterogeneous camera registry (52 cameras across districts,
vendors, protocols and lifecycles), demo incidents, evidence, watchlist
entities and a handful of pre-rolled alerts so every dashboard renders
meaningful information immediately after startup.
"""

from __future__ import annotations

import base64
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Alert, Camera, Detection, Evidence, Incident, VideoJob, WatchlistEntity
from app.services.plates import normalize_plate

logger = get_logger("seed")

_NOW = datetime.now(timezone.utc)

# --------------------------------------------------------------------------
# Gujarat Smart City Corridor — the demo test-vehicle route (GJ plate).
# In id order these six cameras form a believable highway route, so the
# "Run demo test" simulation produces a clean cross-camera movement trail.
# --------------------------------------------------------------------------
DEMO_ROUTE_CAMERA_IDS = ["CAM-09", "CAM-10", "CAM-11", "CAM-12", "CAM-13", "CAM-14"]
DEMO_TEST_PLATE = "GJ 01 AB 1234"

_DEMO_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBk"
    "SEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAB"
    "AAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAA"
    "AAD/2gAIAQEAAD8AVN//2Q=="
)


def _random_hash() -> str:
    import hashlib
    return hashlib.sha256(random.randbytes(32)).hexdigest()


def _random_sha256() -> str:
    return f"SHA256: {_random_hash()}"


def _past(minutes: int) -> datetime:
    return _NOW - timedelta(minutes=minutes)


# --------------------------------------------------------------------------
# Phase 6 heterogeneous registry templates
# --------------------------------------------------------------------------
_CAMERA_TEMPLATES: list[dict[str, Any]] = [
    {"name": "District Command View", "type": "visual", "resolution": "1080p", "fps": 30,
     "vendor": "Hikvision", "model": "DS-2CD2686G2", "vms": "Milestone XProtect",
     "protocol": "rtsp", "caps": ["detection", "tracking", "anpr"]},
    {"name": "Arterial Junction", "type": "visual", "resolution": "4K UHD", "fps": 60,
     "vendor": "Dahua", "model": "SD8A840V-HNF", "vms": "Genetec Security Center",
     "protocol": "rtsp", "caps": ["detection", "speed", "vehicle-classification", "anpr"]},
    {"name": "Perimeter Thermal", "type": "thermal", "resolution": "640x512", "fps": 25,
     "vendor": "Hikvision", "model": "DS-2TD6267", "vms": "Milestone XProtect",
     "protocol": "onvif", "caps": ["intrusion", "perimeter", "heat-mapping"]},
    {"name": "PTZ Overwatch", "type": "ptz", "resolution": "1080p", "fps": 30,
     "vendor": "Axis", "model": "Q6215-LE", "vms": "Axis Companion",
     "protocol": "rtsp", "caps": ["detection", "tracking", "object-tracking"]},
    {"name": "License Plate Reader", "type": "license_plate", "resolution": "1080p", "fps": 60,
     "vendor": "Bosch", "model": "AUTODOME IP 5000i", "vms": "Bosch BVMS",
     "protocol": "rtsp", "caps": ["anpr", "vehicle-classification", "speed"]},
    {"name": "Highway Gantry", "type": "visual", "resolution": "4K UHD", "fps": 60,
     "vendor": "Uniview", "model": "IPC4243-X322", "vms": "ORBISCUDA",
     "protocol": "rtsp", "caps": ["anpr", "speed", "vehicle-classification", "detection"]},
    {"name": "Metro Concourse", "type": "visual", "resolution": "1080p", "fps": 30,
     "vendor": "CP Plus", "model": "CP-RC4-Q30", "vms": "CCTV Custom",
     "protocol": "hls", "caps": ["detection", "crowd-density", "tracking"]},
    {"name": "Fisheye Parking", "type": "fisheye", "resolution": "1440p", "fps": 25,
     "vendor": "Hanwha", "model": "XNF-8010RV", "vms": "Hanwha Wisenet",
     "protocol": "onvif", "caps": ["detection", "lot-occupancy", "anpr"]},
    {"name": "Old Analog Gate", "type": "visual", "resolution": "720p", "fps": 25,
     "vendor": "CP Plus", "model": "CP-UNC-T40", "vms": "NVR Local",
     "protocol": "rtsp", "caps": ["detection"]},
    {"name": "Coverage Gap Watch", "type": "visual", "resolution": "1080p", "fps": 30,
     "vendor": "Dahua", "model": "IPC-HFW2439T", "vms": "Genetec Security Center",
     "protocol": "rtsp", "caps": ["detection", "tracking"]},
]

_DISTRICTS: list[tuple[str, float, float]] = [
    ("Gurugram", 28.470, 77.030),
    ("New Delhi", 28.610, 77.210),
    ("Noida", 28.570, 77.320),
    ("Mumbai", 19.080, 72.880),
    ("Pune", 18.520, 73.860),
    ("Bengaluru", 12.970, 77.590),
    ("Hyderabad", 17.390, 78.490),
    ("Chennai", 13.080, 80.270),
    ("Kolkata", 22.570, 88.360),
    ("Jaipur", 26.910, 75.790),
    ("Lucknow", 26.850, 80.950),
    ("Chandigarh", 30.730, 76.780),
    ("Bhopal", 23.260, 77.410),
    ("Indore", 22.720, 75.860),
    ("Dehradun", 30.320, 78.030),
    ("Patna", 25.610, 85.140),
    ("Ranchi", 23.340, 85.310),
    ("Bhubaneswar", 20.290, 85.820),
    ("Guwahati", 26.140, 91.740),
    ("Ahmedabad", 23.020, 72.570),
    ("Surat", 21.170, 72.830),
    ("Rajkot", 22.300, 70.800),
]

_ROAD_SUFFIXES = ["SP Ring Road", "NH-48 Corridor", "Main Boulevard", "Sector Road", "Station Road", "Promenade"]
_ZONE_NAMES = ["Zone A", "Zone B", "Zone C", "Zone D"]

_LIFECYCLES: list[tuple[str, float]] = [("ACTIVE", 0.78), ("DEGRADED", 0.10), ("MAINTENANCE", 0.07), ("OFFLINE", 0.05)]
_STATUS_FROM_LIFECYCLE = {
    "ACTIVE": "online", "DEGRADED": "warning", "OFFLINE": "offline",
    "MAINTENANCE": "warning", "DISABLED": "offline",
}


def _demographic_caps() -> list[str]:
    return ["detection", "tracking"]


# --------------------------------------------------------------------------
# Explicit cameras (the original demo eight + the Gujarat corridor).
# --------------------------------------------------------------------------
CAMERAS_DATA: list[dict[str, Any]] = [
    {
        "id": "CAM-01", "name": "Main Road Junction",
        "location": "Sector 14, Gurugram - Main Road Junction",
        "status": "online", "fps": 30, "resolution": "1080p",
        "sector": "Sector 14", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "speed"],
        "detections": {"people": 14, "vehicles": 8, "motorcycles": 2},
        "stream_url": "rtsp://10.14.1.1:554/H265", "health": 98.7, "bitrate": 8.4,
        "vendor": "Hikvision", "model": "DS-2CD2686G2", "vms_source": "Milestone XProtect", "protocol": "rtsp",
        "latitude": 28.4701, "longitude": 77.0350, "district": "Gurugram", "zone": "Zone A", "road": "NH-48 Corridor",
        "lifecycle_status": "ACTIVE", "firmware": "v5.8.0", "capabilities": ["detection", "tracking", "speed"],
    },
    {
        "id": "CAM-02", "name": "Connaught Place Gate",
        "location": "Connaught Place, New Delhi - North Perimeter Gate",
        "status": "online", "fps": 30, "resolution": "720p",
        "sector": "Connaught Place", "camera_type": "thermal",
        "ai_capabilities": ["intrusion", "perimeter", "heat-mapping"],
        "detections": {"people": 3, "vehicles": 0, "motorcycles": 0},
        "stream_url": "rtsp://10.14.2.1:554/thermal", "health": 97.1, "bitrate": 4.2,
        "vendor": "Hikvision", "model": "DS-2TD6267", "vms_source": "Milestone XProtect", "protocol": "onvif",
        "latitude": 28.6315, "longitude": 77.2174, "district": "New Delhi", "zone": "Zone A", "road": "Main Boulevard",
        "lifecycle_status": "ACTIVE", "firmware": "v4.9.1", "capabilities": ["intrusion", "perimeter", "heat-mapping"],
    },
    {
        "id": "CAM-03", "name": "IGI Airport Terminal 3",
        "location": "New Delhi - IGI Airport Terminal 3 Plaza",
        "status": "online", "fps": 30, "resolution": "1080p",
        "sector": "IGI Airport", "camera_type": "visual",
        "ai_capabilities": ["detection", "crowd-density", "tracking"],
        "detections": {"people": 87, "vehicles": 12, "motorcycles": 1},
        "stream_url": "rtsp://10.14.3.1:554/H265", "health": 99.2, "bitrate": 9.1,
        "vendor": "Axis", "model": "P3245-LVE", "vms_source": "Genetec Security Center", "protocol": "onvif",
        "latitude": 28.5562, "longitude": 77.1000, "district": "New Delhi", "zone": "Zone B", "road": "NH-48 Corridor",
        "lifecycle_status": "ACTIVE", "firmware": "v10.2.0", "capabilities": ["detection", "crowd-density", "tracking"],
    },
    {
        "id": "CAM-04", "name": "NH-48 Entry Toll",
        "location": "Dharuhera Toll Plaza, NH-48, Haryana",
        "status": "online", "fps": 60, "resolution": "4K UHD",
        "sector": "NH-48", "camera_type": "visual",
        "ai_capabilities": ["detection", "speed", "vehicle-classification", "anpr"],
        "detections": {"people": 0, "vehicles": 64, "motorcycles": 8},
        "stream_url": "rtsp://10.14.4.1:554/H265/4k", "health": 99.5, "bitrate": 28.6,
        "vendor": "Bosch", "model": "AUTODOME IP 5000i", "vms_source": "Bosch BVMS", "protocol": "rtsp",
        "latitude": 28.4418, "longitude": 76.8060, "district": "Gurugram", "zone": "Zone A", "road": "NH-48 Corridor",
        "lifecycle_status": "ACTIVE", "firmware": "v7.5.3", "capabilities": ["detection", "speed", "vehicle-classification", "anpr"],
    },
    {
        "id": "CAM-05", "name": "Noida Sector 62 Office Park",
        "location": "Noida Sector 62 - IT Park South Entrance",
        "status": "online", "fps": 30, "resolution": "1080p",
        "sector": "Noida SEZ", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "loitering"],
        "detections": {"people": 32, "vehicles": 6, "motorcycles": 0},
        "stream_url": "rtsp://10.14.5.1:554/H265", "health": 98.9, "bitrate": 8.2,
        "vendor": "Hanwha", "model": "XNF-8010RV", "vms_source": "Hanwha Wisenet", "protocol": "onvif",
        "latitude": 28.6219, "longitude": 77.3650, "district": "Noida", "zone": "Zone C", "road": "Sector Road",
        "lifecycle_status": "ACTIVE", "firmware": "v2.1.4", "capabilities": ["detection", "tracking", "loitering"],
    },
    {
        "id": "CAM-06", "name": "Marine Drive Promenade",
        "location": "Marine Drive, Mumbai - Promenade CCTV",
        "status": "online", "fps": 30, "resolution": "1080p",
        "sector": "Marine Drive", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "loitering"],
        "detections": {"people": 19, "vehicles": 3, "motorcycles": 0},
        "stream_url": "rtsp://10.14.6.1:554/H265", "health": 97.4, "bitrate": 7.8,
        "vendor": "CP Plus", "model": "CP-RC4-Q30", "vms_source": "Genetec Security Center", "protocol": "rtsp",
        "latitude": 18.9440, "longitude": 72.8234, "district": "Mumbai", "zone": "Zone A", "road": "Marine Drive",
        "lifecycle_status": "ACTIVE", "firmware": "v6.0.2", "capabilities": ["detection", "tracking", "loitering"],
    },
    {
        "id": "CAM-07", "name": "MG Road Metro Gate B",
        "location": "MG Road, Bengaluru - Metro Station Gate B",
        "status": "online", "fps": 60, "resolution": "1080p",
        "sector": "MG Road", "camera_type": "visual",
        "ai_capabilities": ["detection", "intrusion", "tracking"],
        "detections": {"people": 21, "vehicles": 4, "motorcycles": 1},
        "stream_url": "rtsp://10.14.7.1:554/H265", "health": 99.8, "bitrate": 12.4,
        "vendor": "Dahua", "model": "SD8A840V-HNF", "vms_source": "NICE", "protocol": "rtsp",
        "latitude": 12.9752, "longitude": 77.6052, "district": "Bengaluru", "zone": "Zone B", "road": "Main Boulevard",
        "lifecycle_status": "ACTIVE", "firmware": "v3.2.5", "capabilities": ["detection", "intrusion", "tracking"],
    },
    {
        "id": "CAM-08", "name": "Sadar Bazaar Market",
        "location": "Sadar Bazaar, Jaipur - Market Road East",
        "status": "online", "fps": 30, "resolution": "1080p",
        "sector": "Sadar Bazaar", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "crowd-density"],
        "detections": {"people": 54, "vehicles": 18, "motorcycles": 6},
        "stream_url": "rtsp://10.14.8.1:554/H265", "health": 98.1, "bitrate": 8.9,
        "vendor": "Uniview", "model": "IPC4243-X322", "vms_source": "ORBISCUDA", "protocol": "hls",
        "latitude": 26.9190, "longitude": 75.8000, "district": "Jaipur", "zone": "Zone D", "road": "Station Road",
        "lifecycle_status": "DEGRADED", "firmware": "v5.1.1", "capabilities": ["detection", "tracking", "crowd-density"],
    },
]

# Gujarat Smart City Corridor — the demo test-vehicle route.
_GUJARAT_CORRIDOR: list[dict[str, Any]] = [
    {
        "id": "CAM-09", "name": "NH-8 Expressway KM 44", "location": "NH-8 Expressway, Ahmedabad - KM 44 Gantry",
        "status": "online", "fps": 60, "resolution": "4K UHD", "sector": "NH-8", "camera_type": "license_plate",
        "ai_capabilities": ["anpr", "speed", "vehicle-classification"],
        "detections": {"people": 0, "vehicles": 55, "motorcycles": 6},
        "stream_url": "rtsp://10.24.9.1:554/4k", "health": 99.3, "bitrate": 26.4,
        "vendor": "Bosch", "model": "AUTODOME IP 5000i", "vms_source": "Bosch BVMS", "protocol": "rtsp",
        "latitude": 23.0420, "longitude": 72.5130, "district": "Ahmedabad", "zone": "Zone A", "road": "NH-48 Corridor",
        "lifecycle_status": "ACTIVE", "firmware": "v7.5.3", "capabilities": ["anpr", "speed", "vehicle-classification"],
    },
    {
        "id": "CAM-10", "name": "NSDL Toll Plaza", "location": "NSDL Toll Plaza, NH-8 Expressway",
        "status": "online", "fps": 60, "resolution": "4K UHD", "sector": "NH-8", "camera_type": "license_plate",
        "ai_capabilities": ["anpr", "speed", "vehicle-classification"],
        "detections": {"people": 0, "vehicles": 47, "motorcycles": 4},
        "stream_url": "rtsp://10.24.10.1:554/4k", "health": 99.1, "bitrate": 25.9,
        "vendor": "Dahua", "model": "ITC462-PW6M", "vms_source": "Genetec Security Center", "protocol": "rtsp",
        "latitude": 23.0550, "longitude": 72.4980, "district": "Ahmedabad", "zone": "Zone A", "road": "NH-48 Corridor",
        "lifecycle_status": "ACTIVE", "firmware": "v4.0.1", "capabilities": ["anpr", "speed", "vehicle-classification"],
    },
    {
        "id": "CAM-11", "name": "SP Ring Road Junction", "location": "S.P. Ring Road, Ahmedabad - Junction Camera",
        "status": "online", "fps": 30, "resolution": "1080p", "sector": "SP Ring Rd", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "vehicle-classification"],
        "detections": {"people": 9, "vehicles": 31, "motorcycles": 5},
        "stream_url": "rtsp://10.24.11.1:554/H265", "health": 98.5, "bitrate": 9.2,
        "vendor": "Axis", "model": "Q6215-LE", "vms_source": "Milestone XProtect", "protocol": "onvif",
        "latitude": 23.0600, "longitude": 72.5510, "district": "Ahmedabad", "zone": "Zone B", "road": "SP Ring Road",
        "lifecycle_status": "ACTIVE", "firmware": "v10.7.0", "capabilities": ["detection", "tracking", "vehicle-classification"],
    },
    {
        "id": "CAM-12", "name": "Infocity GIFT Junction", "location": "GIFT City Infocity, Gandhinagar - Junction",
        "status": "online", "fps": 30, "resolution": "1080p", "sector": "GIFT City", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking", "anpr"],
        "detections": {"people": 11, "vehicles": 22, "motorcycles": 2},
        "stream_url": "rtsp://10.24.12.1:554/H265", "health": 99.0, "bitrate": 8.8,
        "vendor": "Hanwha", "model": "XNP-6400", "vms_source": "Hanwha Wisenet", "protocol": "rtsp",
        "latitude": 23.2450, "longitude": 72.6340, "district": "Gujarat", "zone": "Zone A", "road": "Main Boulevard",
        "lifecycle_status": "ACTIVE", "firmware": "v3.3.0", "capabilities": ["detection", "tracking", "anpr"],
    },
    {
        "id": "CAM-13", "name": "Secretariat Gate", "location": "Gandhinagar Secretariat Gate - Perimeter",
        "status": "online", "fps": 30, "resolution": "720p", "sector": "Gandhinagar", "camera_type": "thermal",
        "ai_capabilities": ["intrusion", "perimeter", "anpr"],
        "detections": {"people": 2, "vehicles": 8, "motorcycles": 0},
        "stream_url": "rtsp://10.24.13.1:554/thermal", "health": 96.8, "bitrate": 3.9,
        "vendor": "Hikvision", "model": "DS-2TD6267-50QL", "vms_source": "NICE", "protocol": "onvif",
        "latitude": 23.2360, "longitude": 72.6330, "district": "Gujarat", "zone": "Zone A", "road": "Station Road",
        "lifecycle_status": "ACTIVE", "firmware": "v4.9.4", "capabilities": ["intrusion", "perimeter", "anpr"],
    },
    {
        "id": "CAM-14", "name": "Ring Road South Overpass", "location": "S.P. Ring Road South Overpass, Ahmedabad",
        "status": "warning", "fps": 30, "resolution": "1080p", "sector": "SP Ring Rd", "camera_type": "visual",
        "ai_capabilities": ["detection", "tracking"],
        "detections": {"people": 5, "vehicles": 17, "motorcycles": 3},
        "stream_url": "rtsp://10.24.14.1:554/H265", "health": 94.2, "bitrate": 7.3,
        "vendor": "CP Plus", "model": "CP-RC4-Q30", "vms_source": "ORBISCUDA", "protocol": "hls",
        "latitude": 23.0210, "longitude": 72.5890, "district": "Ahmedabad", "zone": "Zone B", "road": "SP Ring Road",
        "lifecycle_status": "DEGRADED", "firmware": "v6.0.2", "capabilities": ["detection", "tracking"],
    },
]


def _generate_extra_cameras(count: int = 38) -> list[dict[str, Any]]:
    """Deterministically generate the remaining heterogeneous cameras."""
    rng = random.Random(52)
    out: list[dict[str, Any]] = []
    for i in range(count):
        cam_id = f"CAM-{15 + i:02d}"
        tpl = _CAMERA_TEMPLATES[i % len(_CAMERA_TEMPLATES)]
        district, base_lat, base_lon = _DISTRICTS[i % len(_DISTRICTS)]
        lat = round(base_lat + rng.uniform(-0.04, 0.04), 5)
        lon = round(base_lon + rng.uniform(-0.05, 0.05), 5)
        lifecycle, _ = _weighted(rng, _LIFECYCLES)
        status = _STATUS_FROM_LIFECYCLE[lifecycle]
        road = _ROAD_SUFFIXES[i % len(_ROAD_SUFFIXES)]
        zone = _ZONE_NAMES[i % len(_ZONE_NAMES)]
        health = round(rng.uniform(88.0, 99.9), 1)
        type_lbl = tpl["type"]
        demog = {"people": rng.randint(0, 25), "vehicles": rng.randint(0, 20), "motorcycles": rng.randint(0, 6)}
        out.append({
            "id": cam_id,
            "name": f'{district} {tpl["name"]} #{i % 9 + 1}',
            "location": f"{district} - {road}, Base Tower {i % 3 + 1}",
            "status": status,
            "fps": tpl["fps"], "resolution": tpl["resolution"],
            "sector": district, "camera_type": type_lbl,
            "ai_capabilities": tpl["caps"] + [_demographic_caps()[0]],
            "detections": demog,
            "stream_url": f"rtsp://10.24.{15 + i}.{rng.randint(2, 20)}:554/stream",
            "health": health, "bitrate": round(rng.uniform(3.0, 12.0), 1),
            "vendor": tpl["vendor"], "model": tpl["model"], "vms_source": tpl["vms"], "protocol": tpl["protocol"],
            "latitude": lat, "longitude": lon, "district": district, "zone": zone, "road": road,
            "lifecycle_status": lifecycle,
            "firmware": f"v{rng.randint(2, 10)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}",
            "capabilities": tpl["caps"],
        })
    return out


def _weighted(rng: random.Random, options: list[tuple[str, float]]) -> tuple[str, float]:
    total = sum(w for _, w in options)
    r = rng.uniform(0, total)
    acc = 0.0
    for value, w in options:
        acc += w
        if r <= acc:
            return value, w
    return options[0]


INCIDENTS_DATA: list[dict[str, Any]] = [
    {
        "id": "INC-1042", "type": "Restricted Zone Entry", "severity": "critical",
        "status": "investigating", "camera_id": "CAM-07",
        "location": "MG Road, Bengaluru - Metro Station Gate B",
        "detected_at": _past(3), "confidence": 0.964,
        "description": "Unauthorized individual detected entering restricted zone through Gate B perimeter.",
        "assigned_to": "Officer D. Sharma",
    },
    {
        "id": "INC-1041", "type": "Crowd Density Threshold Exceeded", "severity": "high",
        "status": "open", "camera_id": "CAM-08",
        "location": "Sadar Bazaar, Jaipur - Market Road East",
        "detected_at": _past(7), "confidence": 0.912,
        "description": "Crowd density at Sadar Bazaar market has exceeded safe threshold by 140%.",
    },
    {
        "id": "INC-1040", "type": "Vehicle Stopped on Express Lane", "severity": "medium",
        "status": "investigating", "camera_id": "CAM-04",
        "location": "NH-48 Toll Plaza, Dharuhera, Haryana",
        "detected_at": _past(14), "confidence": 0.887,
        "description": "Stationary vehicle detected on NH-48 for more than 8 minutes.",
        "assigned_to": "Officer R. Patel",
    },
    {
        "id": "INC-1039", "type": "Abandoned Unattended Object", "severity": "medium",
        "status": "investigating", "camera_id": "CAM-05",
        "location": "Noida Sector 62 - IT Park South Entrance",
        "detected_at": _past(20), "confidence": 0.931,
        "description": "Unattended package detected near office park entrance. No owner in vicinity.",
        "assigned_to": "Officer K. Singh",
    },
    {
        "id": "INC-1038", "type": "Wrong Way Movement", "severity": "high",
        "status": "open", "camera_id": "CAM-03",
        "location": "IGI Airport Terminal 3 Plaza",
        "detected_at": _past(25), "confidence": 0.978,
        "description": "Pedestrian detected moving against designated flow in terminal corridor.",
    },
    {
        "id": "INC-1037", "type": "Perimeter Fence Touch Sensor Alert", "severity": "low",
        "status": "resolved", "camera_id": "CAM-02",
        "location": "Connaught Place, New Delhi - North Perimeter Gate",
        "detected_at": _past(35), "confidence": 0.825,
        "description": "Fence touch sensor triggered. Thermal camera confirmed maintenance crew.",
        "assigned_to": "Officer S. Gupta",
    },
    {
        "id": "INC-1036", "type": "Stalled Delivery Van", "severity": "low",
        "status": "resolved", "camera_id": "CAM-01",
        "location": "Sector 14, Gurugram - Main Road Junction",
        "detected_at": _past(50), "confidence": 0.853,
        "description": "White delivery van stationary for 15+ minutes. Driver completing delivery.",
        "assigned_to": "Officer D. Sharma",
    },
    {
        "id": "INC-1035", "type": "Unusual Loitering Behavior", "severity": "medium",
        "status": "investigating", "camera_id": "CAM-08",
        "location": "Sadar Bazaar, Jaipur - Market Road East",
        "detected_at": _past(22), "confidence": 0.798,
        "description": "Individual exhibiting unusual loitering pattern near market storefronts.",
        "assigned_to": "Officer A. Desai",
    },
    {
        "id": "INC-1034", "type": "Speed Violation Detected (>80km/h)", "severity": "high",
        "status": "open", "camera_id": "CAM-04",
        "location": "NH-48 Toll Plaza, Dharuhera, Haryana",
        "detected_at": _past(38), "confidence": 0.991,
        "description": "Motorcycle recorded traveling at 112 km/h in posted 80 km/h zone.",
    },
    {
        "id": "INC-1033", "type": "Crosswalk Pedestrian Count Anomaly", "severity": "low",
        "status": "resolved", "camera_id": "CAM-05",
        "location": "Noida Sector 62 - IT Park South Entrance",
        "detected_at": _past(60), "confidence": 0.746,
        "description": "Pedestrian count exceeded normal evening average by 220%. Post-event crowd surge.",
    },
    {
        "id": "INC-1032", "type": "Package Left Behind", "severity": "medium",
        "status": "open", "camera_id": "CAM-06",
        "location": "Marine Drive, Mumbai - Promenade CCTV",
        "detected_at": _past(18), "confidence": 0.904,
        "description": "Medium-sized package detected left unattended near parking area.",
    },
    {
        "id": "INC-1031", "type": "Aggressive Gesture Detected", "severity": "high",
        "status": "investigating", "camera_id": "CAM-08",
        "location": "Sadar Bazaar, Jaipur - Market Road East",
        "detected_at": _past(15), "confidence": 0.876,
        "description": "Aggressive physical gestures detected between two individuals in the market.",
        "assigned_to": "Officer T. Reddy",
    },
    {
        "id": "INC-1030", "type": "Routine Perimeter Check Clear", "severity": "low",
        "status": "resolved", "camera_id": "CAM-02",
        "location": "Connaught Place, New Delhi - North Perimeter Gate",
        "detected_at": _past(90), "confidence": 0.99,
        "description": "Scheduled perimeter scan completed. No anomalies detected.",
        "assigned_to": "Officer S. Gupta",
    },
    {
        "id": "INC-1029", "type": "Unauthorized Vehicle in Loading Zone", "severity": "medium",
        "status": "open", "camera_id": "CAM-05",
        "location": "Noida Sector 62 - IT Park South Entrance",
        "detected_at": _past(21), "confidence": 0.942,
        "description": "Non-commercial vehicle detected in restricted loading zone.",
    },
    {
        "id": "INC-1028", "type": "Camera Lens Obstruction Suspected", "severity": "low",
        "status": "resolved", "camera_id": "CAM-01",
        "location": "Sector 14, Gurugram - Main Road Junction",
        "detected_at": _past(110), "confidence": 0.713,
        "description": "Feed quality showed temporary image degradation. Likely condensation.",
    },
]

EVIDENCE_DATA: list[dict[str, Any]] = [
    {
        "id": "EVD-2847", "incident_id": "INC-1042", "camera_id": "CAM-07",
        "type": "video_clip", "title": "Gate B Intrusion Capture",
        "file_path": "uploads/evidence/demo_EVD-2847.mp4", "file_size": 50551808,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(3), "officer": "Officer D. Sharma",
    },
    {
        "id": "EVD-2848", "incident_id": "INC-1041", "camera_id": "CAM-08",
        "type": "snapshot", "title": "Market Road Overhead Crowd Shot",
        "file_path": "uploads/evidence/demo_EVD-2848.jpg", "file_size": 2516582,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(7), "officer": None,
    },
    {
        "id": "EVD-2849", "incident_id": "INC-1040", "camera_id": "CAM-04",
        "type": "video_clip", "title": "NH-48 Stopped Vehicle Capture",
        "file_path": "uploads/evidence/demo_EVD-2849.mp4", "file_size": 118065152,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(14), "officer": "Officer R. Patel",
    },
    {
        "id": "EVD-2850", "incident_id": "INC-1039", "camera_id": "CAM-05",
        "type": "snapshot", "title": "Unattended Package - IT Park",
        "file_path": "uploads/evidence/demo_EVD-2850.jpg", "file_size": 3250585,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(20), "officer": "Officer K. Singh",
    },
    {
        "id": "EVD-2851", "incident_id": "INC-1038", "camera_id": "CAM-03",
        "type": "video_clip", "title": "Terminal 3 Counter-Flow Capture",
        "file_path": "uploads/evidence/demo_EVD-2851.mp4", "file_size": 34291712,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(25), "officer": None,
    },
    {
        "id": "EVD-2852", "incident_id": "INC-1034", "camera_id": "CAM-04",
        "type": "video_clip", "title": "Speed Violation - 112 km/h Motorcycle",
        "file_path": "uploads/evidence/demo_EVD-2852.mp4", "file_size": 9332326,
        "hash": _random_sha256(), "verification_status": "verified",
        "captured_at": _past(38), "officer": "Officer R. Patel",
    },
    {
        "id": "EVD-2853", "incident_id": "INC-1031", "camera_id": "CAM-08",
        "type": "audio", "title": "Market Road Confrontation Audio",
        "file_path": "uploads/evidence/demo_EVD-2853.aac", "file_size": 4404019,
        "hash": _random_sha256(), "verification_status": "pending",
        "captured_at": _past(15), "officer": "Officer T. Reddy",
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(Camera).count() > 0:
        logger.debug("Seed data already present, skipping.")
        return

    logger.info("Seeding development data...")
    _seed_cameras(db)
    _seed_incidents(db)
    _seed_evidence(db)
    _seed_watchlist(db)
    db.commit()
    logger.info("Seed data committed.")


def _seed_cameras(db: Session) -> None:
    all_cams = CAMERAS_DATA + _GUJARAT_CORRIDOR + _generate_extra_cameras()
    for cam_data in all_cams:
        payload = dict(cam_data)
        lifecycle = payload.get("lifecycle_status") or Camera.LIFECYCLE_FROM_STATUS.get(payload.get("status", "online"), "ACTIVE")
        payload["lifecycle_status"] = lifecycle
        cam = Camera(
            id=payload["id"],
            name=payload["name"],
            location=payload["location"],
            status=payload.get("status", "online"),
            stream_url=payload.get("stream_url", ""),
            resolution=payload.get("resolution", "1080p"),
            fps=payload.get("fps", 30),
            ai_enabled=True,
            sector=payload.get("sector"),
            camera_type=payload.get("camera_type", "visual"),
            ai_capabilities=payload.get("ai_capabilities", []),
            health=payload.get("health", 100.0),
            bitrate=payload.get("bitrate", 0.0),
            last_seen=_NOW - timedelta(seconds=random.randint(5, 30)),
            detections=payload.get("detections", {"people": 0, "vehicles": 0}),
            # Phase 6 registry fields
            vendor=payload.get("vendor"),
            model=payload.get("model"),
            vms_source=payload.get("vms_source"),
            protocol=payload.get("protocol", "rtsp"),
            lifecycle_status=lifecycle,
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            district=payload.get("district"),
            zone=payload.get("zone"),
            road=payload.get("road"),
            last_heartbeat=_NOW - timedelta(seconds=random.randint(2, 20)),
            firmware=payload.get("firmware"),
            capabilities=payload.get("capabilities", payload.get("ai_capabilities", [])),
        )
        db.add(cam)


def _seed_incidents(db: Session) -> None:
    existing = {e for (e,) in db.query(Incident.id).all()}
    for inc_data in INCIDENTS_DATA:
        if inc_data["id"] in existing:
            continue
        inc = Incident(
            id=inc_data["id"],
            type=inc_data["type"],
            severity=inc_data["severity"],
            status=inc_data["status"],
            camera_id=inc_data.get("camera_id"),
            location=inc_data.get("location"),
            detected_at=inc_data.get("detected_at", _NOW),
            confidence=inc_data.get("confidence", 0.9),
            description=inc_data.get("description"),
            assigned_to=inc_data.get("assigned_to"),
            metadata_json={
                "timeline": [
                    {
                        "time": inc_data["detected_at"].strftime("%H:%M:%S"),
                        "event": "Event triggered by CV model inference.",
                        "type": "system",
                    }
                ],
                "hash": _random_sha256(),
                "badge_number": None,
            },
        )
        db.add(inc)


def _seed_evidence(db: Session) -> None:
    settings = get_settings()
    evidence_dir = settings.evidence_path()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    existing = {e for (e,) in db.query(Evidence.id).all()}
    for ev_data in EVIDENCE_DATA:
        if ev_data["id"] in existing:
            continue
        name = Path(ev_data["file_path"]).name
        dest = evidence_dir / name
        payload = _DEMO_JPEG if name.endswith(".jpg") else b"SENTINEL AI demo evidence placeholder\n" + name.encode()
        dest.write_bytes(payload)
        db.add(
            Evidence(
                id=ev_data["id"],
                incident_id=ev_data.get("incident_id"),
                camera_id=ev_data.get("camera_id"),
                type=ev_data["type"],
                file_path=str(dest),
                file_size=dest.stat().st_size,
                hash=ev_data["hash"],
                verification_status=ev_data.get("verification_status", "pending"),
                captured_at=ev_data.get("captured_at", _NOW),
                officer=ev_data.get("officer"),
                title=ev_data.get("title"),
            )
        )


WATCHLIST_DATA: list[dict[str, Any]] = [
    {
        "id": "WL-5001", "category": "vehicle", "name": "Test Vehicle - GJ 01 AB 1234",
        "status": "active", "priority": "critical",
        "vehicle_registration": DEMO_TEST_PLATE, "plate_normalized": normalize_plate(DEMO_TEST_PLATE),
        "vehicle_type": "sedan", "vehicle_make": "Toyota", "vehicle_model": "Camry", "vehicle_colour": "silver",
        "notes": "Designated demo test vehicle for the Phase 6 end-to-end showcase. Run 'demo test' in the Command Center to see it tracked across the Gujarat corridor.",
    },
    {
        "id": "WL-5002", "category": "vehicle", "name": "Suspect Vehicle - MH 12 CD 5678",
        "status": "active", "priority": "high",
        "vehicle_registration": "MH 12 CD 5678", "plate_normalized": normalize_plate("MH 12 CD 5678"),
        "vehicle_type": "suv", "vehicle_make": "Mahindra", "vehicle_model": "Scorpio", "vehicle_colour": "black",
        "notes": "Linked to a mobile fraud investigation (FIR 0142/26).",
    },
    {
        "id": "WL-5003", "category": "vehicle", "name": "Stolen Bike - KA 01 XY 2024",
        "status": "active", "priority": "high",
        "vehicle_registration": "KA 01 XY 2024", "plate_normalized": normalize_plate("KA 01 XY 2024"),
        "vehicle_type": "motorcycle", "vehicle_make": "Royal Enfield", "vehicle_colour": "red",
        "notes": "Stolen from Indiranagar (case BL-1187).",
    },
    {
        "id": "WL-5004", "category": "person", "name": "Person of Interest - Rakesh V.",
        "status": "active", "priority": "medium",
        "person_age_range": "35-45", "person_gender": "male", "person_clothing": "navy jacket, cap",
        "notes": "Seen near multiple pick-pocket clusters in Bengaluru.",
    },
]


def _seed_watchlist(db: Session) -> None:
    for data in WATCHLIST_DATA:
        ent = WatchlistEntity(
            id=data["id"], category=data["category"], name=data["name"],
            status=data["status"], priority=data["priority"],
            vehicle_registration=data.get("vehicle_registration"),
            vehicle_type=data.get("vehicle_type"),
            vehicle_make=data.get("vehicle_make"),
            vehicle_model=data.get("vehicle_model"),
            vehicle_colour=data.get("vehicle_colour"),
            plate_normalized=data.get("plate_normalized"),
            person_age_range=data.get("person_age_range"),
            person_gender=data.get("person_gender"),
            person_clothing=data.get("person_clothing"),
            person_remarks=data.get("person_remarks"),
            aliases=data.get("aliases", []),
            reference_images=data.get("reference_images", []),
            notes=data.get("notes"),
            created_at=_NOW,
            updated_at=_NOW,
        )
        db.add(ent)