"""
Health & readiness endpoints.

Kubernetes / Docker / load balancers probe these:
- /health  → process is alive (liveness)
- /ready   → dependencies (DB, Redis) are reachable (readiness)

Never hide dependency failures behind a blanket 200 in readiness checks.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import Settings, get_settings
from app.database.session import get_db

router = APIRouter(tags=["Health"])


def _check_database(db: Session) -> dict[str, Any]:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "up"}
    except Exception as exc:  # noqa: BLE001 — surface any connectivity failure
        return {"status": "down", "error": str(exc)}


def _check_redis(settings: Settings) -> dict[str, Any]:
    try:
        client = Redis.from_url(settings.redis_connection_url, socket_connect_timeout=2)
        pong = client.ping()
        client.close()
        return {"status": "up" if pong else "down"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "error": str(exc)}


@router.get("/health", summary="Liveness probe")
def health(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    """Process is running. Does not check external dependencies."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready", summary="Readiness probe")
def ready(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """
    Returns 200 only when Postgres and Redis respond.
    Returns 503 if any critical dependency is down.
    """
    database = _check_database(db)
    redis = _check_redis(settings)
    healthy = database.get("status") == "up" and redis.get("status") == "up"

    payload = {
        "status": "ready" if healthy else "degraded",
        "checks": {
            "database": database,
            "redis": redis,
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    code = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)
