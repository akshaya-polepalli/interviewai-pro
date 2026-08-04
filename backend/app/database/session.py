"""
SQLAlchemy engine and session factory.

Models live on `app.database.base.Base`. This module owns the engine
and request-scoped sessions only.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.database.base import Base

settings = get_settings()


def _build_engine() -> Engine:
    """
    Create an engine tuned for the active dialect.

    SQLite (used in unit tests) rejects QueuePool kwargs like `max_overflow`.
    Postgres gets a real connection pool with pre-ping for stale connections.
    """
    uri = settings.sqlalchemy_database_uri
    echo = settings.app_debug and settings.app_env == "development"

    if uri.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(
            uri,
            echo=echo,
            connect_args=connect_args,
            poolclass=StaticPool,
        )

    return create_engine(
        uri,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=echo,
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "SessionLocal", "engine", "get_db"]
