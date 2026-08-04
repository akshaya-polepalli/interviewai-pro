"""Interview request/response schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DifficultyLevel, InterviewStatus, InterviewType, TargetCompany, TargetRole


class CreateInterviewRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    interview_type: InterviewType = InterviewType.TECHNICAL
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    target_role: TargetRole | None = TargetRole.SOFTWARE_ENGINEER
    target_company: TargetCompany | None = TargetCompany.GENERAL
    question_count: int = Field(default=5, ge=1, le=10)


class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    answer_text: str = Field(min_length=1, max_length=20000)
    time_spent_seconds: int | None = Field(default=None, ge=0, le=7200)
    code_snippet: str | None = Field(default=None, max_length=50000)
    language: str | None = Field(default=None, max_length=32)


class EvaluateInterviewRequest(BaseModel):
    sync: bool = True


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    question_id: UUID
    answer_text: str | None
    transcript: str | None = None
    has_audio: bool = False
    code_snippet: str | None = None
    language: str | None = None
    time_spent_seconds: int | None = None
    score: Decimal | None = None
    evaluation: dict | None = None
    created_at: datetime


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sequence: int
    category: str
    difficulty: str | None = None
    prompt: str
    expected_points: list | None = None
    is_follow_up: bool = False
    answers: list[AnswerResponse] = Field(default_factory=list)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    overall_score: Decimal | None = None
    technical_score: Decimal | None = None
    communication_score: Decimal | None = None
    confidence_score: Decimal | None = None
    star_method_score: Decimal | None = None
    strengths: list | None = None
    improvements: list | None = None
    detailed_feedback: str | None = None
    model_provider: str | None = None
    model_name: str | None = None


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    interview_type: str
    status: str
    difficulty: str
    target_role: str | None = None
    target_company: str | None = None
    overall_score: Decimal | None = None
    summary: str | None = None
    question_count: int = 0
    answered_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = None
    created_at: datetime
    updated_at: datetime


class InterviewDetailResponse(InterviewResponse):
    questions: list[QuestionResponse] = Field(default_factory=list)
    feedback: FeedbackResponse | None = None
    config: dict | None = None


class EvaluateAcceptedResponse(BaseModel):
    interview_id: UUID
    status: str
    message: str
    overall_score: Decimal | None = None
