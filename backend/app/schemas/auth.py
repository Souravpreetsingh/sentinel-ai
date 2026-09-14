"""Auth + audit schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["ADMIN", "OPERATOR", "INVESTIGATOR", "VIEWER", "AUDITOR"]


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserCreate(BaseModel):
    email: str
    name: str
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = "VIEWER"
    badge_number: str | None = None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    role: UserRole | None = None
    badge_number: str | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: str
    email: str
    name: str
    role: str
    badge_number: str | None = None
    is_active: bool = True
    last_login_at: datetime | None = None


class AuditRead(BaseModel):
    id: int
    actor: str | None = None
    action: str
    resource: str | None = None
    resource_id: str | None = None
    ip: str | None = None
    outcome: str = "success"
    details: dict = Field(default_factory=dict)
    created_at: datetime