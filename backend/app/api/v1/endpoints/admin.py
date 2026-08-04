"""Admin endpoints — require admin permissions."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import CurrentUser, DbSession, require_permissions
from app.models import User
from app.models.enums import UserStatus
from app.schemas.auth import MessageResponse
from app.schemas.pagination import Page
from app.schemas.users import (
    AdminStatsResponse,
    AdminUserDetail,
    AdminUserUpdateRequest,
    PermissionResponse,
    RoleResponse,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin"])

AdminAccess = Annotated[User, Depends(require_permissions("admin:access"))]
AdminUsers = Annotated[User, Depends(require_permissions("admin:users"))]
AdminAnalytics = Annotated[User, Depends(require_permissions("admin:analytics"))]


def _service(db: DbSession) -> AdminService:
    return AdminService(db)


@router.get("/stats", response_model=AdminStatsResponse, summary="Platform statistics")
def stats(_admin: AdminAnalytics, db: DbSession) -> AdminStatsResponse:
    return _service(db).stats()


@router.get("/users", response_model=Page[AdminUserDetail], summary="List users")
def list_users(
    _admin: AdminUsers,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    status_filter: UserStatus | None = Query(None, alias="status"),
    role: str | None = Query(None),
    include_deleted: bool = Query(False),
) -> Page[AdminUserDetail]:
    return _service(db).list_users(
        page=page,
        page_size=page_size,
        search=search,
        status=status_filter,
        role=role,
        include_deleted=include_deleted,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail, summary="Get user detail")
def get_user(user_id: UUID, _admin: AdminUsers, db: DbSession) -> AdminUserDetail:
    return _service(db).get_user(user_id)


@router.patch("/users/{user_id}", response_model=AdminUserDetail, summary="Update user status/roles")
def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    admin: AdminUsers,
    db: DbSession,
) -> AdminUserDetail:
    return _service(db).update_user(user_id, payload, actor_id=admin.id)


@router.delete("/users/{user_id}", response_model=MessageResponse, summary="Soft-delete a user")
def delete_user(user_id: UUID, admin: AdminUsers, db: DbSession) -> MessageResponse:
    _service(db).soft_delete_user(user_id, actor_id=admin.id)
    return MessageResponse(message="User deleted")


@router.get("/roles", response_model=list[RoleResponse], summary="List roles")
def list_roles(_admin: AdminAccess, db: DbSession) -> list[RoleResponse]:
    return _service(db).list_roles()


@router.get("/permissions", response_model=list[PermissionResponse], summary="List permissions")
def list_permissions(_admin: AdminAccess, db: DbSession) -> list[PermissionResponse]:
    return _service(db).list_permissions()
