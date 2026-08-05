"""Settings helpers used by free / PaaS deploys."""

from __future__ import annotations

from app.core.config import Settings


def test_neon_database_url_rewrites_to_psycopg() -> None:
    settings = Settings(
        database_url="postgresql://user:pass@ep-x.neon.tech/neondb?sslmode=require"
    )
    assert settings.sqlalchemy_database_uri.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.sqlalchemy_database_uri


def test_postgres_scheme_rewrites() -> None:
    settings = Settings(database_url="postgres://user:pass@host:5432/db")
    assert settings.sqlalchemy_database_uri.startswith("postgresql+psycopg://")


def test_force_sync_jobs_default_false() -> None:
    settings = Settings()
    assert settings.force_sync_jobs is False
