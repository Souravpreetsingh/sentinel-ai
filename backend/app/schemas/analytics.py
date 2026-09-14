"""Analytics schemas.

Kept intentionally forgiving so the responses can grow as real AI generated
statistics replace the development dataset.

Responses serialize with camelCase keys (e.g. ``hourlyTraffic``) to match the
existing Analytics front-end page, while the underlying model attributes stay
snake_case (``populate_by_name`` accepts either casing on input).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


def to_camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class HourlyPoint(_CamelModel):
    hour: str
    pedestrians: int = 0
    vehicles: int = 0
    incidents: int = 0


class WeeklyPoint(_CamelModel):
    day: str
    detections: int = 0
    incidents: int = 0
    resolved: int = 0


class EventCategory(_CamelModel):
    category: str
    count: int = 0


class CameraUtilizationPoint(_CamelModel):
    camera_id: str
    utilization: float = 0.0
    uptime: float = 0.0


class AiModelPerformance(_CamelModel):
    yolo_version: str = "yolo11n"
    average_inference: str = "—"
    accuracy: float = 0.0
    false_positive_rate: float = 0.0
    models_loaded: int = 0
    gpu_memory: str = "—"
    gpu_temp: int = 0


class TrafficStats(_CamelModel):
    total_pedestrians: int = 0
    total_vehicles: int = 0
    total_incidents: int = 0
    peak_vehicles_hour: str | None = None
    peak_pedestrians_hour: str | None = None


class EventHourActivity(_CamelModel):
    hour: str
    count: int = 0


class AnalyticsOverview(_CamelModel):
    people_detected: int = 0
    vehicles_detected: int = 0
    events: int = 0
    critical_incidents: int = 0
    open_incidents: int = 0
    cameras_online: int = 0
    cameras_total: int = 0

    event_categories: list[EventCategory] = Field(default_factory=list)
    hourly_activity: list[HourlyPoint] = Field(default_factory=list)

    hourly_traffic: list[HourlyPoint] = Field(default_factory=list)
    weekly_trend: list[WeeklyPoint] = Field(default_factory=list)
    top_event_types: list[EventCategory] = Field(default_factory=list)
    camera_utilization: list[CameraUtilizationPoint] = Field(default_factory=list)
    ai_model_performance: AiModelPerformance = Field(default_factory=AiModelPerformance)


class AnalyticsEvents(_CamelModel):
    total_events: int = 0
    event_categories: list[EventCategory] = Field(default_factory=list)
    hourly_activity: list[EventHourActivity] = Field(default_factory=list)
    critical_events: int = 0
    high_severity_events: int = 0


class AnalyticsTraffic(_CamelModel):
    traffic_stats: TrafficStats = Field(default_factory=TrafficStats)
    hourly_traffic: list[HourlyPoint] = Field(default_factory=list)
    weekly_trend: list[WeeklyPoint] = Field(default_factory=list)
    event_categories: list[EventCategory] = Field(default_factory=list)


class AnalyticsCameras(_CamelModel):
    cameras_total: int = 0
    cameras_online: int = 0
    cameras_warning: int = 0
    ai_enabled_count: int = 0
    camera_utilization: list[CameraUtilizationPoint] = Field(default_factory=list)
    cameras: list[dict] = Field(default_factory=list)