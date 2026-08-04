"""AI mock interview endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.interviews import (
    CreateInterviewRequest,
    EvaluateAcceptedResponse,
    EvaluateInterviewRequest,
    InterviewDetailResponse,
    InterviewResponse,
    SubmitAnswerRequest,
)
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/interviews", tags=["Interviews"])

InterviewWriter = Annotated[User, Depends(require_permissions("interviews:write"))]
InterviewReader = Annotated[User, Depends(require_permissions("interviews:read"))]


def _service(db: DbSession) -> InterviewService:
    return InterviewService(db)


@router.get("", response_model=list[InterviewResponse], summary="List my interviews")
def list_interviews(user: InterviewReader, db: DbSession) -> list[InterviewResponse]:
    return _service(db).list_mine(user.id)


@router.post(
    "",
    response_model=InterviewDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a mock interview with generated questions",
)
def create_interview(
    payload: CreateInterviewRequest,
    user: InterviewWriter,
    db: DbSession,
) -> InterviewDetailResponse:
    return _service(db).create(user.id, payload)


@router.get("/{interview_id}", response_model=InterviewDetailResponse, summary="Get interview detail")
def get_interview(
    interview_id: UUID, user: InterviewReader, db: DbSession
) -> InterviewDetailResponse:
    return _service(db).get_mine(user.id, interview_id)


@router.post(
    "/{interview_id}/start",
    response_model=InterviewDetailResponse,
    summary="Start an interview session",
)
def start_interview(
    interview_id: UUID, user: InterviewWriter, db: DbSession
) -> InterviewDetailResponse:
    return _service(db).start(user.id, interview_id)


@router.post(
    "/{interview_id}/answers",
    response_model=InterviewDetailResponse,
    summary="Submit or update an answer",
)
def submit_answer(
    interview_id: UUID,
    payload: SubmitAnswerRequest,
    user: InterviewWriter,
    db: DbSession,
) -> InterviewDetailResponse:
    return _service(db).submit_answer(user.id, interview_id, payload)


@router.post(
    "/{interview_id}/answers/voice",
    response_model=InterviewDetailResponse,
    summary="Submit a voice answer (audio + optional client transcript)",
)
async def submit_voice_answer(
    interview_id: UUID,
    user: InterviewWriter,
    db: DbSession,
    question_id: Annotated[UUID, Form()],
    transcript: Annotated[str | None, Form()] = None,
    time_spent_seconds: Annotated[int | None, Form()] = None,
    audio: UploadFile | None = File(default=None),
) -> InterviewDetailResponse:
    audio_bytes: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    if audio is not None and audio.filename:
        audio_bytes = await audio.read()
        filename = audio.filename
        content_type = audio.content_type
    return _service(db).submit_voice_answer(
        user.id,
        interview_id,
        question_id=question_id,
        audio=audio_bytes,
        filename=filename,
        content_type=content_type,
        client_transcript=transcript,
        time_spent_seconds=time_spent_seconds,
    )


@router.get(
    "/{interview_id}/answers/{answer_id}/audio",
    summary="Download recorded answer audio",
)
def download_answer_audio(
    interview_id: UUID,
    answer_id: UUID,
    user: InterviewReader,
    db: DbSession,
) -> Response:
    data, content_type = _service(db).get_answer_audio(user.id, interview_id, answer_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="answer-{answer_id}.webm"'},
    )


@router.post(
    "/{interview_id}/complete",
    response_model=EvaluateAcceptedResponse | InterviewDetailResponse,
    summary="Complete interview and optionally evaluate",
)
def complete_interview(
    interview_id: UUID,
    user: InterviewWriter,
    db: DbSession,
    evaluate: bool = Query(True),
    sync: bool = Query(True),
) -> EvaluateAcceptedResponse | InterviewDetailResponse:
    return _service(db).complete(user.id, interview_id, evaluate=evaluate, sync=sync)


@router.post(
    "/{interview_id}/evaluate",
    response_model=EvaluateAcceptedResponse,
    summary="Run AI / heuristic evaluation",
)
def evaluate_interview(
    interview_id: UUID,
    payload: EvaluateInterviewRequest,
    user: InterviewWriter,
    db: DbSession,
) -> EvaluateAcceptedResponse:
    return _service(db).evaluate(user.id, interview_id, sync=payload.sync)


@router.delete("/{interview_id}", response_model=MessageResponse, summary="Delete interview")
def delete_interview(
    interview_id: UUID, user: InterviewWriter, db: DbSession
) -> MessageResponse:
    _service(db).delete(user.id, interview_id)
    return MessageResponse(message="Interview deleted")
