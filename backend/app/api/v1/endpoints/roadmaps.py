"""Company prep roadmap endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.roadmaps import (
    CompanyTrackDetail,
    CompanyTrackSummary,
    EnrollRoadmapRequest,
    ToggleMilestoneRequest,
)
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])

RoadmapReader = Annotated[User, Depends(require_permissions("roadmaps:read"))]
RoadmapWriter = Annotated[User, Depends(require_permissions("roadmaps:write"))]


def _service(db: DbSession) -> RoadmapService:
    return RoadmapService(db)


@router.get("", response_model=list[CompanyTrackSummary], summary="List company prep tracks")
def list_roadmaps(user: RoadmapReader, db: DbSession) -> list[CompanyTrackSummary]:
    return _service(db).list_catalog(user.id)


@router.get("/{company}", response_model=CompanyTrackDetail, summary="Get company track detail")
def get_roadmap(company: str, user: RoadmapReader, db: DbSession) -> CompanyTrackDetail:
    return _service(db).get_track(user.id, company)


@router.post(
    "/enroll",
    response_model=CompanyTrackDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll in a company track",
)
def enroll(
    payload: EnrollRoadmapRequest,
    user: RoadmapWriter,
    db: DbSession,
) -> CompanyTrackDetail:
    return _service(db).enroll(user.id, payload)


@router.post(
    "/{company}/milestones",
    response_model=CompanyTrackDetail,
    summary="Manually mark a milestone done/undone",
)
def toggle_milestone(
    company: str,
    payload: ToggleMilestoneRequest,
    user: RoadmapWriter,
    db: DbSession,
) -> CompanyTrackDetail:
    return _service(db).toggle_milestone(
        user.id, company, payload.milestone_id, is_done=payload.is_done
    )


@router.post(
    "/{company}/archive",
    response_model=CompanyTrackDetail,
    summary="Archive enrollment",
)
def archive_roadmap(company: str, user: RoadmapWriter, db: DbSession) -> CompanyTrackDetail:
    return _service(db).archive(user.id, company)
