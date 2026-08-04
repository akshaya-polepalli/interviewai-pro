"""FastAPI dependency injectors."""

from app.dependencies.auth import (
    AuthServiceDep,
    CurrentUser,
    DbSession,
    OAuthServiceDep,
    OptionalUser,
    get_auth_service,
    get_current_user,
    get_oauth_service,
    get_optional_user,
    require_permissions,
)

__all__ = [
    "AuthServiceDep",
    "CurrentUser",
    "DbSession",
    "OAuthServiceDep",
    "OptionalUser",
    "get_auth_service",
    "get_current_user",
    "get_oauth_service",
    "get_optional_user",
    "require_permissions",
]
