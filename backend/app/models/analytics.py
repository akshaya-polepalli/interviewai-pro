"""Per-user analytics rollup for dashboards."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Analytics(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Denormalized counters + skill radar payload.

    Updated by services after interviews/submissions (eventual consistency OK).
    Historical series can live in `weekly_series` JSONB until we split a facts table.
    """

    __tablename__ = "analytics"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_interviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    completed_interviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    average_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    coding_submissions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    coding_accepted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    longest_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    strong_topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    weak_topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    skill_radar: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    weekly_series: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    monthly_series: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    roadmap: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user: Mapped[User] = relationship(back_populates="analytics")
