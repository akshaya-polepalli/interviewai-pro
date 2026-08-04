"""Resume API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ResumeAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    ats_score: Decimal | None = None
    keyword_match_score: Decimal | None = None
    matched_keywords: list | None = None
    missing_keywords: list | None = None
    suggestions: list | None = None
    section_scores: dict | None = None
    model_provider: str | None = None
    model_name: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    content_type: str
    file_size_bytes: int
    status: str
    storage_backend: str
    created_at: datetime
    updated_at: datetime
    word_count: int | None = None
    has_analysis: bool = False
    analysis: ResumeAnalysisResponse | None = None


class ResumeDetailResponse(ResumeResponse):
    raw_text_preview: str | None = None
    parsed_json: dict | None = None


class AnalyzeResumeRequest(BaseModel):
    target_role: str | None = Field(default=None, max_length=64)
    job_description: str | None = Field(default=None, max_length=12000)
    sync: bool = Field(
        default=False,
        description="If true, analyze in-request (useful for demos/tests). Default enqueues Celery.",
    )


class AnalyzeAcceptedResponse(BaseModel):
    message: str
    resume_id: UUID
    status: str
    task_id: str | None = None
    analysis: ResumeAnalysisResponse | None = None
