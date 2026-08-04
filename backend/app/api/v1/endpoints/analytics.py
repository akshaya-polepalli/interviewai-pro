"""User analytics and achievements endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.analytics import AchievementItem, AnalyticsBundleResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

AnalyticsReader = Annotated[User, Depends(require_permissions("users:read"))]


def _service(db: DbSession) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/me", response_model=AnalyticsBundleResponse, summary="My progress analytics")
def my_analytics(
    user: AnalyticsReader,
    db: DbSession,
    refresh: bool = Query(False, description="Recompute rollups from source tables"),
) -> AnalyticsBundleResponse:
    return _service(db).get_bundle(user.id, refresh=True if refresh else False)


@router.post("/me/refresh", response_model=AnalyticsBundleResponse, summary="Recompute my analytics")
def refresh_analytics(user: AnalyticsReader, db: DbSession) -> AnalyticsBundleResponse:
    return _service(db).get_bundle(user.id, refresh=True)


@router.get("/achievements", response_model=list[AchievementItem], summary="My achievements")
def my_achievements(user: AnalyticsReader, db: DbSession) -> list[AchievementItem]:
    return _service(db).list_achievements(user.id)
