"""Coding problems catalog (LeetCode-style bank)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import DifficultyLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.submission import Submission


class CodingProblem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Problem definition with public + hidden test cases.

    Hidden cases are never sent to the client; only verdict aggregates return.
    """

    __tablename__ = "coding_problems"

    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    statement_md: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="coding_difficulty", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)
    starter_code: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    public_tests: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    hidden_tests: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    time_limit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=2000, server_default="2000")
    memory_limit_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=256, server_default="256")
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    company_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String(64)), nullable=True)

    submissions: Mapped[list[Submission]] = relationship(back_populates="problem")
