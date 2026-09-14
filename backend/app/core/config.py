"""Application configuration loaded from the environment.

All secrets and tunables come from environment variables or the .env file.
Nothing sensitive is hardcoded in the source tree.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application -----------------------------------------------------
    app_name: str = "SENTINEL AI"
    service_name: str = "sentinel-ai"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database --------------------------------------------------------
    # e.g. postgresql+psycopg://user:pass@localhost:5432/sentinel
    database_url: str = ""
    use_sqlite: bool = False

    # --- Storage ---------------------------------------------------------
    uploads_dir: str = "uploads"
    videos_dir: str = "videos"

    # --- Upload validation ----------------------------------------------
    max_upload_size_mb: int = 200
    allowed_video_extensions: str = "mp4,mov,avi,mkv,webm,m4v,mpeg"
    allowed_evidence_extensions: str = "mp4,mov,avi,mkv,webm,jpg,jpeg,png,webp,json,txt,wav,mp3,aac"

    # --- AI / detection --------------------------------------------------
    detector_backend: str = "auto"  # auto | yolo | mock
    yolo_model: str = "yolo11n.pt"
    yolo_confidence: float = Field(
        default=0.40,
        validation_alias=AliasChoices("YOLO_CONFIDENCE", "YOLO_CONF_THRESHOLD", "yolo_confidence"),
    )
    yolo_device: str = ""  # empty = auto (CUDA if available, else CPU)

    # --- Inference / frame pipeline --------------------------------------
    ai_process_every_n_frames: int = 2  # AI_PROCESS_EVERY_N_FRAMES
    event_cooldown_seconds: float = 30.0  # EVENT_COOLDOWN_SECONDS

    # --- Rule-based analytics thresholds ---------------------------------
    crowd_low_max: int = 15
    crowd_medium_max: int = 30
    crowd_high_threshold: int = 31  # CROWD_HIGH_THRESHOLD
    abandoned_object_seconds: float = 30.0  # ABANDONED_OBJECT_SECONDS
    abandoned_object_classes: str = "bag,backpack,suitcase,box"
    vehicle_stopped_seconds: float = 20.0  # VEHICLE_STOPPED_SECONDS
    fall_velocity_threshold: float = 6.0
    traffic_congestion_threshold: float = 0.75  # density ratio (0..1)

    # --- Output / debugging ----------------------------------------------
    generate_output_video: bool = False  # GENERATE_OUTPUT_VIDEO
    ai_debug: bool = False  # AI_DEBUG - save annotated frames
    debug_frame_every_n: int = 60
    debug_frames_dir: str = ""
    processed_videos_dir: str = ""
    videos_demo_dir: str = ""

    # --- Job / workers ---------------------------------------------------
    background_worker: bool = True
    worker_poll_seconds: float = 1.0

    # --- WebSocket -------------------------------------------------------
    ws_simulation: bool = False

    # --- Watchlist / matching ---------------------------------------------
    watchlist_fuzzy_tolerance: int = 1  # max edits tolerated for a fuzzy match
    watchlist_min_confidence: float = 0.62  # below -> "no match"
    watchlist_probable_threshold: float = 0.78  # above -> "matched", else "probable match"
    watchlist_exact_threshold: float = 0.98  # normalized exact-equality threshold

    # --- Alert engine ------------------------------------------------------
    alert_cooldown_seconds: float = 120.0  # dedup window per (entity, camera, watchlist)
    alert_track_window_seconds: float = 300.0  # max age to re-use a live track
    alert_critical_min_confidence: float = 0.85  # critical alerts never below this

    # --- Tracking ----------------------------------------------------------
    tracking_reappearance_seconds: float = 600.0  # cross-camera track re-linking window
    tracking_link_similarity: float = 0.85  # min fuzzy/OCR similarity to re-link a track across cameras
    tracking_max_hops: int = 12  # max movement hops kept in an in-memory composite route

    # --- Security ----------------------------------------------------------
    auth_required: bool = False  # enforce JWT + RBAC on all /api routes
    rate_limit_enabled: bool = False  # in-memory per-client IP limiter
    rate_limit_per_minute: int = 600
    jwt_expire_minutes_abs: int = 480
    default_admin_email: str = "admin@sentinel.internal"

    # --- Scale / demo ------------------------------------------------------
    seed_camera_count: int = 52  # representative heterogeneous cameras for demo
    demo_simulation: bool = True  # demo route simulator for the hackathon test drive
    demo_test_plate: str = "GJ 01 AB 1234"  # designated hackathon test vehicle
    scale_worker_pool: int = 8  # simulated AI worker count for scale model

    # --- Misc ------------------------------------------------------------
    secret_key: str = "development-only-key-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # --- Derived helpers -------------------------------------------------
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_video_extensions_list(self) -> list[str]:
        return [e.lower().lstrip(".") for e in self.allowed_video_extensions.split(",") if e.strip()]

    @property
    def allowed_evidence_extensions_list(self) -> list[str]:
        return [e.lower().lstrip(".") for e in self.allowed_evidence_extensions.split(",") if e.strip()]

    @property
    def abandoned_object_class_list(self) -> list[str]:
        return [c.strip().lower() for c in self.abandoned_object_classes.split(",") if c.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_postgres(self) -> bool:
        return bool(self.database_url) and self.database_url.startswith("postgres")

    def resolve_database_url(self) -> str:
        if self.use_sqlite or not self.database_url:
            return f"sqlite:///{PROJECT_ROOT / 'sentinel.db'}"
        if self.database_url.startswith("sqlite:///"):
            raw = self.database_url[len("sqlite:///"):]
            p = Path(raw)
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            return f"sqlite:///{p}"
        return self.database_url

    @property
    def root_dir(self) -> Path:
        return PROJECT_ROOT

    def uploads_path(self) -> Path:
        base = Path(self.uploads_dir)
        return base if base.is_absolute() else PROJECT_ROOT / base

    def videos_path(self) -> Path:
        base = Path(self.videos_dir)
        return base if base.is_absolute() else PROJECT_ROOT / base

    def evidence_path(self) -> Path:
        return self.uploads_path() / "evidence"

    def debug_path(self) -> Path:
        base = Path(self.debug_frames_dir) if self.debug_frames_dir else self.uploads_path() / "debug"
        return base if base.is_absolute() else PROJECT_ROOT / base

    def processed_video_path(self) -> Path:
        base = Path(self.processed_videos_dir) if self.processed_videos_dir else self.uploads_path() / "processed"
        return base if base.is_absolute() else PROJECT_ROOT / base

    def demo_video_path(self) -> Path:
        base = Path(self.videos_demo_dir) if self.videos_demo_dir else self.videos_path() / "demo"
        return base if base.is_absolute() else PROJECT_ROOT / base

    def ensure_dirs(self) -> None:
        for p in (
            self.uploads_path(),
            self.videos_path(),
            self.evidence_path(),
            self.debug_path(),
            self.processed_video_path(),
            self.demo_video_path(),
        ):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()