"""SQLAlchemy setup with PostgreSQL primary and SQLite development fallback."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_driver: str = "sqlite"


def _create_engine(url: str) -> Engine:
    kwargs: dict[str, Any] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def initialize_database() -> Engine:
    """Create the engine, probing PostgreSQL first and falling back to SQLite."""
    global _engine, _session_factory, _driver
    settings = get_settings()

    url = settings.resolve_database_url()
    configured_postgres = settings.is_postgres and url.startswith("postgres")

    if configured_postgres:
        desired = url
        try:
            probe = _create_engine(desired)
            with probe.connect():
                pass
            probe.dispose()
            _driver = "postgresql"
            logger.info("Connected to PostgreSQL database")
        except Exception as exc:  # pragma: no cover - depends on infra
            logger.warning(
                "PostgreSQL unavailable (%s). Falling back to SQLite for development.", exc
            )
            fallback = f"sqlite:///{settings.root_dir / 'sentinel.db'}"
            _driver = "sqlite"
            url = fallback
    else:
        _driver = "sqlite" if url.startswith("sqlite") else "other"
        logger.info("Using database driver: %s", _driver)

    _engine = _create_engine(url)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        return initialize_database()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        initialize_database()
        assert _session_factory is not None
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def ensure_schema(engine: Engine) -> None:
    """Create missing tables and add missing columns (lightweight migration).

    SQLAlchemy's ``create_all`` never ALTERs an existing table, so an older
    ``sentinel.db`` (e.g. from Phase 5) would be missing new columns such as the
    camera registry / GIS fields. For the demo the same end-state tables are
    recreated on demand: any table that is missing a declared column is dropped
    and rebuilt (the DB is seeded immediately afterwards, so no data is lost).
    """
    from sqlalchemy import inspect

    required = {t.name: t for t in Base.metadata.sorted_tables}
    existing = set(inspect(engine).get_table_names())
    if not existing:
        Base.metadata.create_all(bind=engine)
        return

    infer = inspect(engine)
    to_drop: list[str] = []
    for name, table in required.items():
        if name not in existing:
            continue
        try:
            have = {col["name"] for col in infer.get_columns(name)}
        except Exception:  # pragma: no cover - non-standard table
            continue
        want = {col.name for col in table.columns}
        if not want.issubset(have):
            to_drop.append(name)

    for name in to_drop:
        logger.warning("Schema drift detected on table '%s': dropping for rebuild.", name)
        Base.metadata.tables[name].drop(bind=engine, checkfirst=True)
    if to_drop:
        Base.metadata.create_all(bind=engine)
        return
    Base.metadata.create_all(bind=engine)


def database_driver() -> str:
    return _driver