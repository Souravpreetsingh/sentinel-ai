"""Auth + audit API endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from app.core.database import get_db
from app.core.security import Principal, assert_roles, get_current_principal
from app.schemas.auth import AuditRead, LoginRequest, TokenResponse, UserCreate, UserRead, UserUpdate
from app.services import auth_service, audit_service

router = APIRouter(tags=["auth"])

Auth = Annotated[Principal, Depends(get_current_principal)]
Db = Annotated[object, Depends(get_db)]


@router.post("/auth/login", response_model=TokenResponse, summary="Login with email + password")
def login(db: Db, payload: LoginRequest, request: Request, x_audit_actor: str | None = Header(None)):
    user, token = auth_service.authenticate(db, payload.email, payload.password)
    audit_service.record(
        db, action="auth.login", actor=f"{user.id}:{user.email}", resource="auth",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")[:256] if request.headers.get("user-agent") else None,
        outcome="success", details={"role": user.role},
    )
    return TokenResponse(access_token=token, user={
        "id": user.id, "email": user.email, "name": user.name, "role": user.role,
    })


@router.get("/auth/me", response_model=TokenResponse, summary="Current principal", include_in_schema=False)
def me(principal: Auth):
    return TokenResponse(access_token=principal.token, user={
        "id": principal.user_id, "email": principal.email, "name": principal.name, "role": principal.role,
    })


@router.get("/auth/users", response_model=list[UserRead], summary="List users (ADMIN)")
def list_users(db: Db, principal: Auth):
    assert_roles(principal, "ADMIN")
    return auth_service.list_users(db)


@router.post("/auth/users", response_model=UserRead, status_code=201, summary="Create user (ADMIN)")
def create_user(db: Db, principal: Auth, payload: UserCreate, request: Request):
    assert_roles(principal, "ADMIN")
    user = auth_service.create_user(db, payload, actor=principal.user_id)
    audit_service.record(db, action="auth.user_create", actor=principal.user_id,
                         resource="user", resource_id=user.id,
                         ip=request.client.host if request.client else None,
                         details={"role": user.role})
    return user


@router.patch("/auth/users/{user_id}", response_model=UserRead, summary="Update user (ADMIN)")
def update_user(db: Db, principal: Auth, user_id: str, payload: UserUpdate, request: Request):
    assert_roles(principal, "ADMIN")
    user = auth_service.update_user(db, user_id, payload)
    audit_service.record(db, action="auth.user_update", actor=principal.user_id,
                         resource="user", resource_id=user_id,
                         ip=request.client.host if request.client else None)
    return user


@router.delete("/auth/users/{user_id}", status_code=204, summary="Deactivate user (ADMIN)")
def deactivate_user(db: Db, principal: Auth, user_id: str, request: Request):
    assert_roles(principal, "ADMIN")
    user = auth_service.deactivate_user(db, user_id)
    audit_service.record(db, action="auth.user_deactivate", actor=principal.user_id,
                         resource="user", resource_id=user_id,
                         ip=request.client.host if request.client else None)
    return None


@router.get("/audit", response_model=list[AuditRead], summary="List audit log (AUDITOR+)")
def list_audit(
    db: Db,
    principal: Auth,
    actor: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    limit: int = 200,
):
    assert_roles(principal, "AUDITOR", "INVESTIGATOR", "ADMIN")
    return audit_service.list_logs(db, actor=actor, action=action, resource=resource,
                                   outcome=outcome, since=since, limit=limit)


@router.get("/audit/summary", summary="Audit action counts (AUDITOR+)")
def audit_summary(db: Db, principal: Auth, hours: int = 24, limit: int = 200):
    assert_roles(principal, "AUDITOR", "INVESTIGATOR", "ADMIN")
    return audit_service.summarize(db, hours=hours, limit=limit)