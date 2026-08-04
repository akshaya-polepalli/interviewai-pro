"""Analytics schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SkillRadar(BaseModel):
    technical: float = 0
    behavioral: float = 0
    communication: float = 0
    coding: float = 0
    resume: float = 0


class RoadmapItem(BaseModel):
    id: str
    title: str
    done: bool
    hint: str | None = None


class SeriesPoint(BaseModel):
    label: str
    interviews: int = 0
    coding: int = 0
    resumes: int = 0


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    total_interviews: int
    completed_interviews: int
    average_score: Decimal | None = None
    coding_submissions: int
    coding_accepted: int
    current_streak_days: int
    longest_streak_days: int
    strong_topics: list | None = None
    weak_topics: list | None = None
    skill_radar: SkillRadar | dict | None = None
    weekly_series: list[SeriesPoint] | list | None = None
    roadmap: list[RoadmapItem] | dict | list | None = None
    latest_ats_score: Decimal | None = None
    updated_at: datetime | None = None


class AchievementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    description: str
    points: int
    unlocked: bool
    unlocked_at: datetime | None = None


class AnalyticsBundleResponse(BaseModel):
    analytics: AnalyticsResponse
    achievements: list[AchievementItem] = Field(default_factory=list)
    recently_unlocked: list[str] = Field(default_factory=list)
