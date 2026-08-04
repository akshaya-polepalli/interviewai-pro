"""User enrollment in a company-specific prep roadmap."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import RoadmapEnrollmentStatus, TargetCompany
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserCompanyRoadmap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One enrollment per user per company track."""

    __tablename__ = "user_company_roadmaps"
    __table_args__ = (UniqueConstraint("user_id", "company", name="uq_user_company_roadmap"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[TargetCompany] = mapped_column(
        Enum(
            TargetCompany,
            name="roadmap_target_company",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    status: Mapped[RoadmapEnrollmentStatus] = mapped_column(
        Enum(
            RoadmapEnrollmentStatus,
            name="roadmap_enrollment_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=RoadmapEnrollmentStatus.ACTIVE,
        server_default=RoadmapEnrollmentStatus.ACTIVE.value,
        index=True,
    )
    # Milestone IDs the user manually marked done (beyond auto rules).
    manual_done: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="company_roadmaps")
