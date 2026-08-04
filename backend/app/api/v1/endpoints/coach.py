"""AI coach and study plan endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.coach import (
    CoachAskRequest,
    CoachAskResponse,
    CoachInsightResponse,
    CoachMessageResponse,
    GenerateStudyPlanRequest,
    StudyPlanDetailResponse,
    StudyPlanResponse,
    UpdateTaskRequest,
)
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coach", tags=["Coach"])

CoachReader = Annotated[User, Depends(require_permissions("coach:read"))]
CoachWriter = Annotated[User, Depends(require_permissions("coach:write"))]


def _service(db: DbSession) -> CoachService:
    return CoachService(db)


@router.get("/insights", response_model=CoachInsightResponse, summary="Coach insights from analytics")
def coach_insights(user: CoachReader, db: DbSession) -> CoachInsightResponse:
    return _service(db).insights(user.id)


@router.get("/plans", response_model=list[StudyPlanResponse], summary="List my study plans")
def list_plans(user: CoachReader, db: DbSession) -> list[StudyPlanResponse]:
    return _service(db).list_plans(user.id)


@router.post(
    "/plans",
    response_model=StudyPlanDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized study plan",
)
def generate_plan(
    payload: GenerateStudyPlanRequest,
    user: CoachWriter,
    db: DbSession,
) -> StudyPlanDetailResponse:
    return _service(db).generate_plan(user.id, payload)


@router.get("/plans/{plan_id}", response_model=StudyPlanDetailResponse, summary="Get study plan")
def get_plan(plan_id: UUID, user: CoachReader, db: DbSession) -> StudyPlanDetailResponse:
    return _service(db).get_plan(user.id, plan_id)


@router.patch(
    "/plans/{plan_id}/tasks/{task_id}",
    response_model=StudyPlanDetailResponse,
    summary="Mark a study task done/undone",
)
def update_task(
    plan_id: UUID,
    task_id: UUID,
    payload: UpdateTaskRequest,
    user: CoachWriter,
    db: DbSession,
) -> StudyPlanDetailResponse:
    return _service(db).update_task(user.id, plan_id, task_id, is_done=payload.is_done)


@router.post(
    "/plans/{plan_id}/archive",
    response_model=StudyPlanDetailResponse,
    summary="Archive a study plan",
)
def archive_plan(plan_id: UUID, user: CoachWriter, db: DbSession) -> StudyPlanDetailResponse:
    return _service(db).archive_plan(user.id, plan_id)


@router.get("/messages", response_model=list[CoachMessageResponse], summary="Coach chat history")
def list_messages(
    user: CoachReader,
    db: DbSession,
    limit: int = Query(40, ge=1, le=100),
) -> list[CoachMessageResponse]:
    return _service(db).list_messages(user.id, limit=limit)


@router.post("/ask", response_model=CoachAskResponse, summary="Ask the AI coach")
def ask_coach(payload: CoachAskRequest, user: CoachWriter, db: DbSession) -> CoachAskResponse:
    return _service(db).ask(user.id, payload.message)
