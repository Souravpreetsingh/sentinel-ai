"""Shared Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ApiMessage(BaseModel):
    message: str
    code: str = "OK"
    timestamp: datetime | None = None


class ApiError(BaseModel):
    code: str
    message: str
    resource: str | None = None
    identifier: str | None = None
    errors: list[dict[str, Any]] | None = None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)