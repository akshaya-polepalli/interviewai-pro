"""Report request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportType


class CreateReportRequest(BaseModel):
    report_type: ReportType = ReportType.WEEKLY_PROGRESS
    title: str | None = Field(default=None, max_length=255)
    interview_id: UUID | None = None
    resume_id: UUID | None = None
    sync: bool = True
    format: Literal["json", "markdown", "pdf"] = "pdf"


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_type: str
    status: str
    title: str
    content_type: str | None = None
    ready_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    has_file: bool = False


class ReportDetailResponse(ReportResponse):
    payload: dict | None = None


class ReportAcceptedResponse(BaseModel):
    report_id: UUID
    status: str
    message: str
