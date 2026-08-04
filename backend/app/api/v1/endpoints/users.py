"""Authenticated user profile endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import MessageResponse
from app.schemas.users import (
    ChangePasswordRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    SessionResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


def _service(db: DbSession) -> UserService:
    return UserService(db)


@router.get("/me", response_model=ProfileResponse, summary="Get my profile")
def get_me(user: CurrentUser, db: DbSession) -> ProfileResponse:
    return _service(db).get_profile(user.id)


@router.patch("/me", response_model=ProfileResponse, summary="Update my profile")
def update_me(payload: ProfileUpdateRequest, user: CurrentUser, db: DbSession) -> ProfileResponse:
    return _service(db).update_profile(user.id, payload)


@router.post("/me/change-password", response_model=MessageResponse, summary="Change password")
def change_password(payload: ChangePasswordRequest, user: CurrentUser, db: DbSession) -> MessageResponse:
    _service(db).change_password(user.id, payload)
    return MessageResponse(message="Password updated. Please sign in again.")


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete my account",
)
def delete_me(payload: DeleteAccountRequest, user: CurrentUser, db: DbSession) -> MessageResponse:
    _service(db).delete_account(user.id, password=payload.password)
    return MessageResponse(message="Account deleted")


@router.get("/me/sessions", response_model=list[SessionResponse], summary="List my sessions")
def list_sessions(user: CurrentUser, db: DbSession) -> list[SessionResponse]:
    return _service(db).list_sessions(user.id)


@router.delete(
    "/me/sessions/{session_id}",
    response_model=MessageResponse,
    summary="Revoke one of my sessions",
)
def revoke_session(session_id: UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    _service(db).revoke_session(user.id, session_id)
    return MessageResponse(message="Session revoked")
