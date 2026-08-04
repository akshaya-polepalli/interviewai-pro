"""
Authentication application service.

Owns register / login / refresh / logout / verify / password-reset flows.
Routers stay thin: validate HTTP → call service → return schema.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models import ActivityLog, Analytics, User
from app.models.enums import ActivityAction, UserStatus
from app.repositories import TokenRepository, UserRepository
from app.schemas.auth import TokenResponse, UserPublic
from app.services.email_service import EmailService

logger = get_logger(__name__)


def user_to_public(user: User) -> UserPublic:
    return UserPublic(
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
    )


class AuthService:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.tokens = TokenRepository(db)
        self.email = email_service or EmailService(self.settings)

    def register(self, *, email: str, full_name: str, password: str) -> tuple[User, str]:
        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists")

        role = self.users.get_role_by_name("candidate")
        if role is None:
            raise AppError(
                "Default role 'candidate' is missing. Run the seed script.",
                code="seed_required",
                status_code=500,
            )

        user = self.users.create(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            status=UserStatus.PENDING_VERIFICATION,
            roles=[role],
        )
        self.db.add(Analytics(user_id=user.id))

        raw_verify = generate_opaque_token()
        self.tokens.create_email_verification(
            user_id=user.id,
            token_hash=hash_token(raw_verify),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self.settings.email_verification_expire_hours),
        )
        self._log(user.id, ActivityAction.REGISTER)
        self.db.commit()
        self.db.refresh(user)

        self.email.send_verification(to=user.email, token=raw_verify)
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user, raw_verify

    def forgot_password(self, *, email: str) -> str | None:
        """
        Always succeed from the caller's perspective (anti-enumeration).
        Returns raw reset token only for non-production debug responses.
        """
        user = self.users.get_by_email(email)
        if user is None:
            logger.info("password_reset_unknown_email", email=email.lower())
            return None

        raw = generate_opaque_token()
        self.tokens.create_password_reset(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC)
            + timedelta(hours=self.settings.password_reset_expire_hours),
        )
        self._log(user.id, ActivityAction.PASSWORD_RESET, metadata={"stage": "requested"})
        self.db.commit()
        self.email.send_password_reset(to=user.email, token=raw)
        return raw
    def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenResponse:
        user = self.users.get_by_email(email)
        if user is None or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")

        if user.status == UserStatus.SUSPENDED:
            raise ForbiddenError("Account is suspended")

        user.last_login_at = datetime.now(UTC)
        self.users.save(user)
        tokens = self._issue_token_pair(user, user_agent=user_agent, ip_address=ip_address)
        self._log(user.id, ActivityAction.LOGIN, metadata={"ip": ip_address})
        self.db.commit()
        return tokens

    def login_oauth(
        self,
        *,
        provider: str,
        provider_user_id: str,
        email: str,
        full_name: str,
        avatar_url: str | None,
        email_verified: bool,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenResponse:
        """Find-or-create user from an OAuth profile and issue tokens."""
        email = email.lower().strip()
        user: User | None = None
        if provider == "google":
            user = self.users.get_by_google_sub(provider_user_id)
        elif provider == "github":
            user = self.users.get_by_github_id(provider_user_id)

        if user is None:
            user = self.users.get_by_email(email)
            if user:
                # Link provider to existing email account
                if provider == "google":
                    user.google_sub = provider_user_id
                else:
                    user.github_id = provider_user_id
                if avatar_url and not user.avatar_url:
                    user.avatar_url = avatar_url
                if email_verified and not user.is_email_verified:
                    user.is_email_verified = True
                    user.email_verified_at = datetime.now(UTC)
                    if user.status == UserStatus.PENDING_VERIFICATION:
                        user.status = UserStatus.ACTIVE
                self.users.save(user)
            else:
                candidate = self.users.get_role_by_name("candidate")
                user = self.users.create(
                    email=email,
                    full_name=full_name,
                    hashed_password=None,
                    status=UserStatus.ACTIVE if email_verified else UserStatus.PENDING_VERIFICATION,
                    roles=[candidate] if candidate else None,
                    google_sub=provider_user_id if provider == "google" else None,
                    github_id=provider_user_id if provider == "github" else None,
                    is_email_verified=email_verified,
                    avatar_url=avatar_url,
                )
                if email_verified:
                    user.email_verified_at = datetime.now(UTC)
                self.db.add(Analytics(user_id=user.id))
                self.users.save(user)

        if user.status == UserStatus.SUSPENDED:
            raise ForbiddenError("Account is suspended")

        user.last_login_at = datetime.now(UTC)
        self.users.save(user)
        tokens = self._issue_token_pair(user, user_agent=user_agent, ip_address=ip_address)
        self._log(
            user.id,
            ActivityAction.LOGIN,
            metadata={"ip": ip_address, "provider": provider, "oauth": True},
        )
        self.db.commit()
        return tokens

    def refresh(self, *, refresh_token: str, user_agent: str | None, ip_address: str | None) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        stored = self.tokens.get_refresh_by_hash(token_hash)
        if stored is None:
            raise UnauthorizedError("Invalid refresh token")

        if stored.revoked_at is not None:
            # Reuse detection — possible token theft
            self.tokens.revoke_all_user_refresh_tokens(stored.user_id)
            self.db.commit()
            logger.warning("refresh_token_reuse_detected", user_id=str(stored.user_id))
            raise UnauthorizedError("Refresh token reuse detected; all sessions revoked")

        if stored.expires_at < datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired")

        user = self.users.get_by_id(stored.user_id)
        if user is None or user.status == UserStatus.SUSPENDED:
            raise UnauthorizedError("User unavailable")

        # Rotate: revoke old, issue new bound to same session when possible
        response = self._issue_token_pair(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            session_id=stored.session_id,
        )
        new_row = self.tokens.get_refresh_by_hash(hash_token(response.refresh_token))
        self.tokens.revoke_refresh(
            stored,
            replaced_by_id=new_row.id if new_row else None,
        )
        self.db.commit()
        return response

    def logout(self, *, refresh_token: str | None, user_id: UUID | None, everywhere: bool) -> None:
        if everywhere and user_id:
            self.tokens.revoke_all_user_refresh_tokens(user_id)
            self._log(user_id, ActivityAction.LOGOUT, metadata={"everywhere": True})
            self.db.commit()
            return

        if not refresh_token:
            raise ValidationAppError("refresh_token is required unless everywhere=true")

        stored = self.tokens.get_refresh_by_hash(hash_token(refresh_token))
        if stored:
            self.tokens.revoke_refresh(stored)
            self._log(stored.user_id, ActivityAction.LOGOUT)
            self.db.commit()

    def verify_email(self, *, token: str) -> UserPublic:
        stored = self.tokens.get_email_verification(hash_token(token))
        if stored is None or stored.used_at is not None:
            raise ValidationAppError("Invalid or already used verification token")
        if stored.expires_at < datetime.now(UTC):
            raise ValidationAppError("Verification token expired")

        user = self.users.get_by_id(stored.user_id)
        if user is None:
            raise NotFoundError("User not found")

        now = datetime.now(UTC)
        stored.used_at = now
        user.is_email_verified = True
        user.email_verified_at = now
        if user.status == UserStatus.PENDING_VERIFICATION:
            user.status = UserStatus.ACTIVE
        self.users.save(user)
        self.db.commit()
        self.db.refresh(user)
        return user_to_public(user)

    def reset_password(self, *, token: str, new_password: str) -> None:
        stored = self.tokens.get_password_reset(hash_token(token))
        if stored is None or stored.used_at is not None:
            raise ValidationAppError("Invalid or already used reset token")
        if stored.expires_at < datetime.now(UTC):
            raise ValidationAppError("Reset token expired")

        user = self.users.get_by_id(stored.user_id)
        if user is None:
            raise NotFoundError("User not found")

        stored.used_at = datetime.now(UTC)
        user.hashed_password = hash_password(new_password)
        self.users.save(user)
        self.tokens.revoke_all_user_refresh_tokens(user.id)
        self._log(user.id, ActivityAction.PASSWORD_RESET, metadata={"stage": "completed"})
        self.db.commit()

    def get_me(self, user_id: UUID) -> UserPublic:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user_to_public(user)

    def _issue_token_pair(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
        session_id: UUID | None = None,
    ) -> TokenResponse:
        access_token, _ = create_access_token(
            subject=user.id,
            settings=self.settings,
            extra_claims={
                "email": user.email,
                "roles": [r.name for r in (user.roles or [])],
            },
        )
        refresh_raw = generate_opaque_token(48)
        refresh_expires = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days)

        sid = session_id
        if sid is None:
            session = self.tokens.create_session(
                user_id=user.id,
                expires_at=refresh_expires,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            sid = session.id

        self.tokens.create_refresh_token(
            user_id=user.id,
            session_id=sid,
            token_hash=hash_token(refresh_raw),
            expires_at=refresh_expires,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_raw,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=user_to_public(user),
        )

    def _log(
        self,
        user_id: UUID | None,
        action: ActivityAction,
        *,
        metadata: dict | None = None,
    ) -> None:
        self.db.add(
            ActivityLog(
                user_id=user_id,
                action=action,
                resource_type="auth",
                metadata_json=metadata,
            )
        )
