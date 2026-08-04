"""Admin application service — platform stats and user management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationAppError
from app.models import ActivityLog, Interview, Resume, Submission, User
from app.models.enums import ActivityAction, UserStatus
from app.repositories import TokenRepository, UserRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.pagination import Page
from app.schemas.users import (
    AdminStatsResponse,
    AdminUserDetail,
    AdminUserUpdateRequest,
    PermissionResponse,
    RoleResponse,
)
from app.services.user_service import permissions_for, to_profile


def to_admin_user(user: User) -> AdminUserDetail:
    base = to_profile(user)
    return AdminUserDetail(
        **base.model_dump(),
        is_deleted=user.is_deleted,
        deleted_at=user.deleted_at,
    )


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.sessions = SessionRepository(db)

    def stats(self) -> AdminStatsResponse:
        return AdminStatsResponse(
            total_users=self.users.count_users(),
            active_users=self.users.count_by_status(UserStatus.ACTIVE),
            pending_verification=self.users.count_by_status(UserStatus.PENDING_VERIFICATION),
            suspended_users=self.users.count_by_status(UserStatus.SUSPENDED),
            deleted_users=self.users.count_deleted(),
            verified_users=self.users.count_users(verified_only=True),
            total_interviews=int(self.db.scalar(select(func.count()).select_from(Interview)) or 0),
            total_submissions=int(self.db.scalar(select(func.count()).select_from(Submission)) or 0),
            total_resumes=int(self.db.scalar(select(func.count()).select_from(Resume)) or 0),
            users_by_role=self.users.count_by_role(),
            recent_registrations_7d=self.users.count_registered_since(
                datetime.now(UTC) - timedelta(days=7)
            ),
        )

    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: UserStatus | None,
        role: str | None,
        include_deleted: bool,
    ) -> Page[AdminUserDetail]:
        offset = (page - 1) * page_size
        rows, total = self.users.list_users(
            offset=offset,
            limit=page_size,
            search=search,
            status=status,
            role=role,
            include_deleted=include_deleted,
        )
        return Page.of(
            items=[to_admin_user(u) for u in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_user(self, user_id: UUID) -> AdminUserDetail:
        user = self.users.get_by_id(user_id, include_deleted=True)
        if user is None:
            raise NotFoundError("User not found")
        return to_admin_user(user)

    def update_user(self, user_id: UUID, payload: AdminUserUpdateRequest, *, actor_id: UUID) -> AdminUserDetail:
        user = self.users.get_by_id(user_id, include_deleted=True)
        if user is None:
            raise NotFoundError("User not found")
        if user.is_deleted:
            raise ValidationAppError("Cannot update a deleted user")

        data = payload.model_dump(exclude_unset=True)
        if "full_name" in data and data["full_name"]:
            user.full_name = data["full_name"].strip()

        if "status" in data and data["status"] is not None:
            new_status = data["status"]
            if not isinstance(new_status, UserStatus):
                new_status = UserStatus(new_status)
            # Protect last active admin from suspension
            if (
                new_status in {UserStatus.SUSPENDED, UserStatus.INACTIVE}
                and any(r.name == "admin" for r in (user.roles or []))
            ):
                _, admin_count = self.users.list_users(offset=0, limit=5, role="admin", status=UserStatus.ACTIVE)
                if admin_count <= 1 and user.status == UserStatus.ACTIVE:
                    raise ForbiddenError("Cannot suspend/disable the last active admin")
            user.status = new_status

        if "roles" in data and data["roles"] is not None:
            role_names = data["roles"]
            if not role_names:
                raise ValidationAppError("User must have at least one role")
            roles = []
            for name in role_names:
                role = self.users.get_role_by_name(name)
                if role is None:
                    raise ValidationAppError(f"Unknown role: {name}")
                roles.append(role)
            was_admin = any(r.name == "admin" for r in (user.roles or []))
            will_be_admin = any(r.name == "admin" for r in roles)
            if was_admin and not will_be_admin:
                _, admin_count = self.users.list_users(offset=0, limit=5, role="admin")
                if admin_count <= 1:
                    raise ForbiddenError("Cannot remove the last admin role")
            user.roles = roles

        self.users.save(user)
        self.db.add(
            ActivityLog(
                user_id=actor_id,
                action=ActivityAction.ADMIN_ACTION,
                resource_type="user",
                resource_id=str(user.id),
                metadata_json={"update": data},
            )
        )
        if payload.status == UserStatus.SUSPENDED or (
            isinstance(payload.status, str) and payload.status == UserStatus.SUSPENDED.value
        ):
            self.tokens.revoke_all_user_refresh_tokens(user.id)
            self.sessions.revoke_all_for_user(user.id)

        self.db.commit()
        self.db.refresh(user)
        return to_admin_user(user)

    def soft_delete_user(self, user_id: UUID, *, actor_id: UUID) -> None:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if user.id == actor_id:
            raise ValidationAppError("Use the profile delete endpoint to delete your own account")
        if any(r.name == "admin" for r in (user.roles or [])):
            _, admin_count = self.users.list_users(offset=0, limit=2, role="admin")
            if admin_count <= 1:
                raise ForbiddenError("Cannot delete the last admin account")

        self.users.soft_delete(user)
        self.tokens.revoke_all_user_refresh_tokens(user.id)
        self.sessions.revoke_all_for_user(user.id)
        self.db.add(
            ActivityLog(
                user_id=actor_id,
                action=ActivityAction.ADMIN_ACTION,
                resource_type="user",
                resource_id=str(user.id),
                metadata_json={"action": "soft_delete"},
            )
        )
        self.db.commit()

    def list_roles(self) -> list[RoleResponse]:
        roles = self.users.list_roles()
        return [
            RoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                permissions=[p.code for p in (role.permissions or [])],
            )
            for role in roles
        ]

    def list_permissions(self) -> list[PermissionResponse]:
        return [PermissionResponse.model_validate(p) for p in self.users.list_permissions()]
