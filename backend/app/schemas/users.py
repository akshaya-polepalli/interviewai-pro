"""User profile and admin DTOs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TargetCompany, TargetRole, UserStatus
from app.schemas.auth import UserPublic
from app.schemas.pagination import Page


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=1024)
    target_role: TargetRole | None = None
    target_company: TargetCompany | None = None
    years_of_experience: int | None = Field(default=None, ge=0, le=60)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name is too short")
        return cleaned


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        return value


class ProfileResponse(UserPublic):
    bio: str | None = None
    years_of_experience: int | None = None
    permissions: list[str] = Field(default_factory=list)
    last_login_at: datetime | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_agent: str | None
    ip_address: str | None
    device_label: str | None
    expires_at: datetime
    revoked_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime


class AdminUserUpdateRequest(BaseModel):
    status: UserStatus | None = None
    roles: list[str] | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=200)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_system: bool
    permissions: list[str] = Field(default_factory=list)


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    description: str | None


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    pending_verification: int
    suspended_users: int
    deleted_users: int
    verified_users: int
    total_interviews: int
    total_submissions: int
    total_resumes: int
    users_by_role: dict[str, int]
    recent_registrations_7d: int


class AdminUserDetail(ProfileResponse):
    is_deleted: bool = False
    deleted_at: datetime | None = None


UserPage = Page[AdminUserDetail]
