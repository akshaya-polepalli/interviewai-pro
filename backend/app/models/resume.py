"""Resume upload and AI analysis persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ResumeStatus
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Uploaded resume file metadata + parsing state."""

    __tablename__ = "resumes"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ResumeStatus] = mapped_column(
        Enum(ResumeStatus, name="resume_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ResumeStatus.UPLOADED,
        server_default=ResumeStatus.UPLOADED.value,
        index=True,
    )
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user: Mapped[User] = relationship(back_populates="resumes")
    analysis: Mapped[ResumeAnalysis | None] = relationship(
        back_populates="resume",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ResumeAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    ATS score + keyword gaps + AI suggestions.

    Heavy AI payloads live in JSONB so the schema stays stable while
    prompts/models evolve.
    """

    __tablename__ = "resume_analyses"

    resume_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    ats_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    keyword_match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    matched_keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    missing_keywords: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    suggestions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    section_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    resume: Mapped[Resume] = relationship(back_populates="analysis")
