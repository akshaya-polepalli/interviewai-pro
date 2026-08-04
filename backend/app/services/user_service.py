"""User profile application service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError, ValidationAppError
from app.core.security import hash_password, verify_password
from app.models import ActivityLog, RefreshToken, User
from app.models.enums import ActivityAction, TargetCompany, TargetRole
from app.repositories import TokenRepository, UserRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.users import (
    ChangePasswordRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    SessionResponse,
)


def permissions_for(user: User) -> list[str]:
    codes: set[str] = set()
    for role in user.roles or []:
        for perm in role.permissions or []:
            codes.add(perm.code)
    return sorted(codes)


def to_profile(user: User) -> ProfileResponse:
    return ProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_email_verified=user.is_email_verified,
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        target_role=user.target_role.value if user.target_role else None,
        target_company=user.target_company.value if user.target_company else None,
        roles=[role.name for role in (user.roles or [])],
        created_at=user.created_at,
        bio=user.bio,
        years_of_experience=user.years_of_experience,
        permissions=permissions_for(user),
        last_login_at=user.last_login_at,
    )


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.sessions = SessionRepository(db)

    def get_profile(self, user_id: UUID) -> ProfileResponse:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return to_profile(user)

    def update_profile(self, user_id: UUID, payload: ProfileUpdateRequest) -> ProfileResponse:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        data = payload.model_dump(exclude_unset=True)
        if "full_name" in data and data["full_name"] is not None:
            user.full_name = data["full_name"]
        if "bio" in data:
            user.bio = data["bio"]
        if "avatar_url" in data:
            user.avatar_url = data["avatar_url"]
        if "years_of_experience" in data:
            user.years_of_experience = data["years_of_experience"]
        if "target_role" in data:
            value = data["target_role"]
            user.target_role = value if isinstance(value, TargetRole) or value is None else TargetRole(value)
        if "target_company" in data:
            value = data["target_company"]
            user.target_company = (
                value if isinstance(value, TargetCompany) or value is None else TargetCompany(value)
            )

        self.users.save(user)
        self.db.add(
            ActivityLog(
                user_id=user.id,
                action=ActivityAction.PROFILE_UPDATE,
                resource_type="user",
                resource_id=str(user.id),
            )
        )
        self.db.commit()
        self.db.refresh(user)
        return to_profile(user)

    def change_password(self, user_id: UUID, payload: ChangePasswordRequest) -> None:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if not verify_password(payload.current_password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        if payload.current_password == payload.new_password:
            raise ValidationAppError("New password must be different")

        user.hashed_password = hash_password(payload.new_password)
        self.users.save(user)
        self.tokens.revoke_all_user_refresh_tokens(user.id)
        self.sessions.revoke_all_for_user(user.id)
        self.db.add(
            ActivityLog(
                user_id=user.id,
                action=ActivityAction.PASSWORD_RESET,
                resource_type="user",
                resource_id=str(user.id),
                metadata_json={"stage": "change_password"},
            )
        )
        self.db.commit()

    def delete_account(self, user_id: UUID, *, password: str) -> None:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.hashed_password and not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Password confirmation failed")

        if any(r.name == "admin" for r in (user.roles or [])):
            _, admin_count = self.users.list_users(offset=0, limit=2, role="admin")
            if admin_count <= 1:
                raise ForbiddenError("Cannot delete the last admin account")

        self.users.soft_delete(user)
        self.tokens.revoke_all_user_refresh_tokens(user.id)
        self.sessions.revoke_all_for_user(user.id)
        self.db.add(
            ActivityLog(
                user_id=user.id,
                action=ActivityAction.OTHER,
                resource_type="user",
                resource_id=str(user.id),
                metadata_json={"action": "account_deleted"},
            )
        )
        self.db.commit()

    def list_sessions(self, user_id: UUID) -> list[SessionResponse]:
        return [SessionResponse.model_validate(s) for s in self.sessions.list_for_user(user_id)]

    def revoke_session(self, user_id: UUID, session_id: UUID) -> None:
        session = self.sessions.get_for_user(session_id, user_id)
        if session is None:
            raise NotFoundError("Session not found")
        self.sessions.revoke(session)
        self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.session_id == session_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.commit()
