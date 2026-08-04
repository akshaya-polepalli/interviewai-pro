"""Session listing helpers for the signed-in user."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import UserSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[UserSession]:
        return list(
            self.db.scalars(
                select(UserSession)
                .where(UserSession.user_id == user_id)
                .order_by(UserSession.created_at.desc())
            ).all()
        )

    def get_for_user(self, session_id: UUID, user_id: UUID) -> UserSession | None:
        return self.db.scalar(
            select(UserSession).where(
                UserSession.id == session_id,
                UserSession.user_id == user_id,
            )
        )

    def revoke(self, session: UserSession) -> None:
        session.revoked_at = datetime.now(UTC)
        self.db.add(session)
        self.db.flush()

    def revoke_all_for_user(self, user_id: UUID) -> None:
        self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.flush()
