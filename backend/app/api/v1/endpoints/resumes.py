"""Resume upload, analysis, and download endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response

from app.dependencies import CurrentUser, DbSession, require_permissions
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.resumes import (
    AnalyzeAcceptedResponse,
    AnalyzeResumeRequest,
    ResumeDetailResponse,
    ResumeResponse,
)
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["Resumes"])

ResumeWriter = Annotated[User, Depends(require_permissions("resumes:write"))]
ResumeReader = Annotated[User, Depends(require_permissions("resumes:read"))]


def _service(db: DbSession) -> ResumeService:
    return ResumeService(db)


@router.get("", response_model=list[ResumeResponse], summary="List my resumes")
def list_resumes(user: ResumeReader, db: DbSession) -> list[ResumeResponse]:
    return _service(db).list_mine(user.id)


@router.post(
    "",
    response_model=AnalyzeAcceptedResponse | ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume (PDF/DOCX/TXT)",
)
async def upload_resume(
    user: ResumeWriter,
    db: DbSession,
    file: UploadFile = File(...),
    analyze: bool = Form(True),
    sync: bool = Form(False),
    target_role: str | None = Form(None),
) -> AnalyzeAcceptedResponse | ResumeResponse:
    data = await file.read()
    return _service(db).upload(
        user_id=user.id,
        filename=file.filename or "resume.pdf",
        content_type=file.content_type,
        data=data,
        analyze=analyze,
        sync=sync,
        target_role=target_role,
    )


@router.get("/{resume_id}", response_model=ResumeDetailResponse, summary="Get resume detail")
def get_resume(resume_id: UUID, user: ResumeReader, db: DbSession) -> ResumeDetailResponse:
    return _service(db).get_mine(user.id, resume_id)


@router.post(
    "/{resume_id}/analyze",
    response_model=AnalyzeAcceptedResponse,
    summary="Run / re-run ATS analysis",
)
def analyze_resume(
    resume_id: UUID,
    payload: AnalyzeResumeRequest,
    user: ResumeWriter,
    db: DbSession,
) -> AnalyzeAcceptedResponse:
    return _service(db).analyze(
        user_id=user.id,
        resume_id=resume_id,
        target_role=payload.target_role,
        job_description=payload.job_description,
        sync=payload.sync,
    )


@router.get("/{resume_id}/download", summary="Download original resume file")
def download_resume(resume_id: UUID, user: ResumeReader, db: DbSession) -> Response:
    data, content_type, filename = _service(db).download(user.id, resume_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{resume_id}", response_model=MessageResponse, summary="Soft-delete resume")
def delete_resume(resume_id: UUID, user: ResumeWriter, db: DbSession) -> MessageResponse:
    _service(db).delete(user.id, resume_id)
    return MessageResponse(message="Resume deleted")
