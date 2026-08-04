"""Token / session persistence helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken, UserSession
from app.models.auth_token import EmailVerificationToken, PasswordResetToken


class TokenRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(
        self,
        *,
        user_id: UUID,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> UserSession:
        now = datetime.now(UTC)
        session = UserSession(
            user_id=user_id,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            last_seen_at=now,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def create_refresh_token(
        self,
        *,
        user_id: UUID,
        session_id: UUID | None,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        row = RefreshToken(
            user_id=user_id,
            session_id=session_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def revoke_refresh(self, token: RefreshToken, *, replaced_by_id: UUID | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by_id:
            token.replaced_by_id = replaced_by_id
        self.db.add(token)
        self.db.flush()

    def revoke_all_user_refresh_tokens(self, user_id: UUID) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.flush()

    def create_email_verification(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        row = EmailVerificationToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(row)
        self.db.flush()
        return row

    def get_email_verification(self, token_hash: str) -> EmailVerificationToken | None:
        return self.db.scalar(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )

    def create_password_reset(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        row = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(row)
        self.db.flush()
        return row

    def get_password_reset(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
