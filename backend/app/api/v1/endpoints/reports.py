"""Downloadable report endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.auth import MessageResponse
from app.schemas.reports import (
    CreateReportRequest,
    ReportAcceptedResponse,
    ReportDetailResponse,
    ReportResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])

ReportReader = Annotated[User, Depends(require_permissions("reports:read"))]
# candidates have reports:read; generating uses same gate for MVP
ReportWriter = Annotated[User, Depends(require_permissions("reports:read"))]


def _service(db: DbSession) -> ReportService:
    return ReportService(db)


@router.get("", response_model=list[ReportResponse], summary="List my reports")
def list_reports(user: ReportReader, db: DbSession) -> list[ReportResponse]:
    return _service(db).list_mine(user.id)


@router.post(
    "",
    response_model=ReportAcceptedResponse | ReportDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a progress report",
)
def create_report(
    payload: CreateReportRequest,
    user: ReportWriter,
    db: DbSession,
) -> ReportAcceptedResponse | ReportDetailResponse:
    return _service(db).create(user.id, payload)


@router.get("/{report_id}", response_model=ReportDetailResponse, summary="Get report detail")
def get_report(report_id: UUID, user: ReportReader, db: DbSession) -> ReportDetailResponse:
    return _service(db).get_mine(user.id, report_id)


@router.get("/{report_id}/download", summary="Download report file")
def download_report(report_id: UUID, user: ReportReader, db: DbSession) -> Response:
    data, content_type, filename = _service(db).download(user.id, report_id)
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{report_id}", response_model=MessageResponse, summary="Delete report")
def delete_report(report_id: UUID, user: ReportWriter, db: DbSession) -> MessageResponse:
    _service(db).delete(user.id, report_id)
    return MessageResponse(message="Report deleted")
