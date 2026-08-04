"""Code submissions and per-run execution results."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ProgrammingLanguage, SubmissionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.coding_problem import CodingProblem
    from app.models.user import User


class Submission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One code submission against a coding problem."""

    __tablename__ = "submissions"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("coding_problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[ProgrammingLanguage] = mapped_column(
        Enum(
            ProgrammingLanguage,
            name="programming_language",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=SubmissionStatus.QUEUED,
        server_default=SubmissionStatus.QUEUED.value,
        index=True,
    )
    verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    passed_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="submissions")
    problem: Mapped[CodingProblem] = relationship(back_populates="submissions")
    execution_results: Mapped[list[ExecutionResult]] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class ExecutionResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-test-case outcome for a submission (public + hidden)."""

    __tablename__ = "execution_results"

    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            name="execution_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    stdin: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_kb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    submission: Mapped[Submission] = relationship(back_populates="execution_results")
