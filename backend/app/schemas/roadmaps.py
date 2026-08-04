"""Company roadmap schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TargetCompany


class EnrollRoadmapRequest(BaseModel):
    company: TargetCompany = TargetCompany.GENERAL
    notes: str | None = Field(default=None, max_length=2000)


class ToggleMilestoneRequest(BaseModel):
    milestone_id: str = Field(min_length=1, max_length=64)
    is_done: bool = True


class MilestoneResponse(BaseModel):
    id: str
    title: str
    description: str
    week: int
    category: str
    resource_path: str | None = None
    auto_rule: str | None = None
    done: bool = False
    done_via: str | None = None  # auto | manual | None


class CompanyTrackSummary(BaseModel):
    company: str
    name: str
    tagline: str
    weeks: int
    focus: list[str]
    milestone_count: int
    enrolled: bool = False
    progress_pct: int = 0
    status: str | None = None


class CompanyTrackDetail(BaseModel):
    company: str
    name: str
    tagline: str
    weeks: int
    focus: list[str]
    interview_loop: list[str]
    principles: list[str]
    milestones: list[MilestoneResponse]
    enrolled: bool = False
    enrollment_id: UUID | None = None
    status: str | None = None
    notes: str | None = None
    done_count: int = 0
    milestone_count: int = 0
    progress_pct: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company: str
    status: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
