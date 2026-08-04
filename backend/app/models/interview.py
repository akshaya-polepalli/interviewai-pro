"""Interview sessions, questions, answers, and AI feedback."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import (
    DifficultyLevel,
    InterviewStatus,
    InterviewType,
    QuestionCategory,
    TargetCompany,
    TargetRole,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Interview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One mock interview attempt (tech / behavioral / HR / voice / coding)."""

    __tablename__ = "interviews"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(InterviewType, name="interview_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus, name="interview_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InterviewStatus.DRAFT,
        server_default=InterviewStatus.DRAFT.value,
        index=True,
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_level", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DifficultyLevel.MEDIUM,
        server_default=DifficultyLevel.MEDIUM.value,
    )
    target_role: Mapped[TargetRole | None] = mapped_column(
        Enum(TargetRole, name="interview_target_role", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    target_company: Mapped[TargetCompany | None] = mapped_column(
        Enum(TargetCompany, name="interview_target_company", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="interviews")
    questions: Mapped[list[Question]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="Question.sequence",
    )
    feedback: Mapped[Feedback | None] = relationship(
        back_populates="interview",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single question inside an interview (may have follow-ups via parent_id)."""

    __tablename__ = "questions"

    interview_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[QuestionCategory] = mapped_column(
        Enum(QuestionCategory, name="question_category", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=QuestionCategory.OTHER,
        server_default=QuestionCategory.OTHER.value,
        index=True,
    )
    difficulty: Mapped[DifficultyLevel | None] = mapped_column(
        Enum(
            DifficultyLevel,
            name="question_difficulty",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_points: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    interview: Mapped[Interview] = relationship(back_populates="questions")
    parent: Mapped[Question | None] = relationship(remote_side="Question.id", back_populates="follow_ups")
    follow_ups: Mapped[list[Question]] = relationship(back_populates="parent")
    answers: Mapped[list[Answer]] = relationship(back_populates="question", cascade="all, delete-orphan")


class Answer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Candidate response (text, audio transcript, or code reference)."""

    __tablename__ = "answers"

    question_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    question: Mapped[Question] = relationship(back_populates="answers")


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Holistic AI evaluation for a completed interview."""

    __tablename__ = "feedback"

    interview_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    star_method_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    improvements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    detailed_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    interview: Mapped[Interview] = relationship(back_populates="feedback")
