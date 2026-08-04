"""Coding problems and submissions API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.coding import (
    ProblemDetail,
    ProblemListItem,
    SubmissionResponse,
    SubmitAcceptedResponse,
    SubmitCodeRequest,
)
from app.services.coding_service import CodingService

router = APIRouter(prefix="/coding", tags=["Coding"])

CodingReader = Annotated[User, Depends(require_permissions("coding:read"))]
CodingSubmitter = Annotated[User, Depends(require_permissions("coding:submit"))]


def _service(db: DbSession) -> CodingService:
    return CodingService(db)


@router.get("/problems", response_model=list[ProblemListItem], summary="List coding problems")
def list_problems(user: CodingReader, db: DbSession) -> list[ProblemListItem]:
    return _service(db).list_problems()


@router.get(
    "/problems/by-slug/{slug}",
    response_model=ProblemDetail,
    summary="Get problem by slug",
)
def get_problem_by_slug(slug: str, user: CodingReader, db: DbSession) -> ProblemDetail:
    return _service(db).get_problem_by_slug(slug)


@router.get(
    "/problems/{problem_id}",
    response_model=ProblemDetail,
    summary="Get problem detail (no hidden tests)",
)
def get_problem(problem_id: UUID, user: CodingReader, db: DbSession) -> ProblemDetail:
    return _service(db).get_problem(problem_id)


@router.post(
    "/problems/{problem_id}/submissions",
    response_model=SubmitAcceptedResponse | SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a solution",
)
def submit_solution(
    problem_id: UUID,
    payload: SubmitCodeRequest,
    user: CodingSubmitter,
    db: DbSession,
) -> SubmitAcceptedResponse | SubmissionResponse:
    return _service(db).submit(user.id, problem_id, payload)


@router.get(
    "/submissions",
    response_model=list[SubmissionResponse],
    summary="List my submissions",
)
def list_submissions(
    user: CodingReader,
    db: DbSession,
    problem_id: UUID | None = Query(default=None),
) -> list[SubmissionResponse]:
    return _service(db).list_my_submissions(user.id, problem_id)


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission detail",
)
def get_submission(
    submission_id: UUID, user: CodingReader, db: DbSession
) -> SubmissionResponse:
    return _service(db).get_my_submission(user.id, submission_id)
