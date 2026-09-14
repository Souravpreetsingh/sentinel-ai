"""Pytest configuration.

Wires the application to a temporary SQLite database, mock detector, and
disables background workers / simulators so tests are deterministic.
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# --- Test environment (must be set before app modules are imported) --------
_TMP = tempfile.mkdtemp(prefix="sentinel-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP, 'test.db').replace(chr(92), '/')}"
os.environ["USE_SQLITE"] = "false"
os.environ["WS_SIMULATION"] = "false"
os.environ["BACKGROUND_WORKER"] = "false"
os.environ["DETECTOR_BACKEND"] = "mock"
os.environ["UPLOADS_DIR"] = os.path.join(_TMP, "uploads")
os.environ["VIDEOS_DIR"] = os.path.join(_TMP, "videos")
os.environ["LOG_LEVEL"] = "WARNING"

# Force settings cache rebuild.
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session_factory():
    from app.core.database import get_session_factory
    return get_session_factory()


@pytest.fixture
def db(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.close()