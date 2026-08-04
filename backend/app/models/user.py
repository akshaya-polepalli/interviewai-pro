"""User account model — identity core of the platform."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import TargetCompany, TargetRole, UserStatus
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.rbac import user_roles

if TYPE_CHECKING:
    from app.models.achievement import UserAchievement
    from app.models.activity_log import ActivityLog
    from app.models.analytics import Analytics
    from app.models.auth_token import EmailVerificationToken, PasswordResetToken
    from app.models.interview import Interview
    from app.models.notification import Notification
    from app.models.rbac import Role
    from app.models.refresh_token import RefreshToken
    from app.models.report import Report
    from app.models.resume import Resume
    from app.models.session import UserSession
    from app.models.submission import Submission
    from app.models.coach import CoachMessage, StudyPlan
    from app.models.roadmap import UserCompanyRoadmap
    from app.models.billing import UserSubscription


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Application user.

    Password hashes live here; OAuth-only users may have `hashed_password=NULL`.
    Never store plaintext passwords. Auth flows land in Module 3.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserStatus.PENDING_VERIFICATION,
        server_default=UserStatus.PENDING_VERIFICATION.value,
        index=True,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # OAuth provider subject IDs (nullable until linked)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    github_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    target_role: Mapped[TargetRole | None] = mapped_column(
        Enum(TargetRole, name="target_role", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    target_company: Mapped[TargetCompany | None] = mapped_column(
        Enum(TargetCompany, name="target_company", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )
    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[list[Interview]] = relationship(back_populates="user", cascade="all, delete-orphan")
    submissions: Mapped[list[Submission]] = relationship(back_populates="user", cascade="all, delete-orphan")
    analytics: Mapped[Analytics | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    achievements: Mapped[list[UserAchievement]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(back_populates="user", cascade="all, delete-orphan")
    study_plans: Mapped[list[StudyPlan]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    coach_messages: Mapped[list[CoachMessage]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    company_roadmaps: Mapped[list[UserCompanyRoadmap]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[UserSubscription | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    email_verification_tokens: Mapped[list[EmailVerificationToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
