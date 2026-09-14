"""Audit service — append-only log of sensitive operations."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    outcome: str = "success",
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        resource=resource,
        resource_id=resource_id,
        ip=ip,
        user_agent=user_agent,
        outcome=outcome,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    return entry


def list_logs(
    db: Session,
    *,
    actor: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    outcome: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 200,
) -> list[AuditLog]:
    q = db.query(AuditLog)
    if actor:
        q = q.filter(AuditLog.actor == actor)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource:
        q = q.filter(AuditLog.resource == resource)
    if outcome:
        q = q.filter(AuditLog.outcome == outcome)
    if since:
        q = q.filter(AuditLog.created_at >= since)
    if until:
        q = q.filter(AuditLog.created_at <= until)
    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()


def summarize(db: Session, hours: int = 24, limit: int = 200) -> dict:
    from sqlalchemy import func

    since = datetime.now() - timedelta(hours=hours)
    rows = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.created_at >= since)
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(limit)
        .all()
    )
    total = db.query(func.count(AuditLog.id)).filter(AuditLog.created_at >= since).scalar() or 0
    return {"period_hours": hours, "total": total, "by_action": {a: n for a, n in rows}}