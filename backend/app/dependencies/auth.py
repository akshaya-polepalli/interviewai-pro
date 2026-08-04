"""FastAPI auth dependencies — current user & permission checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models import User
from app.models.enums import UserStatus
from app.repositories import UserRepository
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.oauth_service import OAuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(db: Annotated[Session, Depends(get_db)]) -> AuthService:
    return AuthService(db, email_service=EmailService())


def get_oauth_service() -> OAuthService:
    return OAuthService()


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    db: Session,
    request: Request,
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (ValueError, KeyError):
        return None

    user = UserRepository(db).get_by_id(user_id)
    if user is None or user.is_deleted:
        return None
    if user.status == UserStatus.SUSPENDED:
        raise ForbiddenError("Account is suspended")
    request.state.user_id = str(user.id)
    return user


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user = _user_from_credentials(credentials, db, request)
    if user is None:
        raise UnauthorizedError("Missing or invalid bearer token")
    return user


def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    return _user_from_credentials(credentials, db, request)


def require_permissions(*codes: str) -> Callable[..., User]:
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        granted: set[str] = set()
        for role in user.roles or []:
            for perm in role.permissions or []:
                granted.add(perm.code)
        missing = [c for c in codes if c not in granted]
        if missing:
            raise ForbiddenError(
                "Missing required permissions",
                details={"missing": missing},
            )
        return user

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OAuthServiceDep = Annotated[OAuthService, Depends(get_oauth_service)]
DbSession = Annotated[Session, Depends(get_db)]
