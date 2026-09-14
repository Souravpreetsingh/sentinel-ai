"""Auth service — user lifecycle, login with PBKDF2 + JWT, RBAC helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import not_found
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.auth import UserCreate, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email.ilike(email)).first()


def get_user_by_id(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise not_found("User", user_id)
    return user


def list_users(db: Session, limit: int = 100) -> list[User]:
    return db.query(User).order_by(User.created_at.asc()).limit(limit).all()


def create_user(db: Session, data: UserCreate, actor: str | None = None) -> User:
    existing = get_user_by_email(db, data.email)
    if existing is not None:
        raise HTTPException(status_code=409, detail={"code": "EMAIL_EXISTS", "message": "A user with this email already exists."})
    user = User(
        id=f"U-{uuid.uuid4().hex[:10].upper()}",
        email=data.email.lower().strip(),
        name=data.name,
        role=data.role.upper(),
        password_hash=hash_password(data.password),
        is_active=True,
        badge_number=data.badge_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: str, data: UserUpdate) -> User:
    user = get_user_by_id(db, user_id)
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.password_hash = hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: str) -> User:
    user = get_user_by_id(db, user_id)
    user.is_active = False
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    """Return (user, token) on success; raise 401 otherwise."""
    user = get_user_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."})
    token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    })
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user, token


def ensure_default_admin(db: Session) -> User:
    """Seed a default admin for local/demo mode when no user exists."""
    admin = get_user_by_email(db, "admin@sentinel.local")
    if admin is not None:
        return admin
    from app.schemas.auth import UserCreate
    try:
        return create_user(
            db,
            UserCreate(email="admin@sentinel.local", name="Default Admin",
                       role="ADMIN", password="admin12345", badge_number="A-0001"),
            actor="system",
        )
    except HTTPException:
        user = get_user_by_email(db, "admin@sentinel.local")
        if user is not None:
            return user
        raise