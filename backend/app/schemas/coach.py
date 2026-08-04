"""AI coach and study plan schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenerateStudyPlanRequest(BaseModel):
    weeks: int = Field(default=2, ge=1, le=8)
    title: str | None = Field(default=None, max_length=255)
    focus_areas: list[str] | None = Field(default=None, max_length=12)


class UpdateTaskRequest(BaseModel):
    is_done: bool


class CoachAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class StudyPlanTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    day_offset: int
    title: str
    description: str | None = None
    category: str
    estimated_minutes: int
    resource_path: str | None = None
    is_done: bool
    created_at: datetime
    updated_at: datetime


class StudyPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None = None
    status: str
    weeks: int
    focus_areas: list | None = None
    model_provider: str | None = None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    done_count: int = 0


class StudyPlanDetailResponse(StudyPlanResponse):
    tasks: list[StudyPlanTaskResponse] = Field(default_factory=list)


class CoachMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    extra: dict | None = None
    created_at: datetime


class CoachAskResponse(BaseModel):
    reply: CoachMessageResponse
    history: list[CoachMessageResponse]


class CoachInsightResponse(BaseModel):
    headline: str
    tips: list[str]
    weak_topics: list[str]
    focus_areas: list[str]
    suggested_weeks: int
