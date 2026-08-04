"""
OAuth helpers (Google / GitHub).

Authorize URL + code exchange + profile fetch.
OAuth `state` is stored in Redis (short TTL) to prevent CSRF.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from redis import Redis

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, UnauthorizedError, ValidationAppError
from app.core.logging import get_logger

logger = get_logger(__name__)

OAUTH_STATE_PREFIX = "oauth:state:"
OAUTH_STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class OAuthProfile:
    provider: str
    provider_user_id: str
    email: str
    full_name: str
    avatar_url: str | None = None
    email_verified: bool = True


class OAuthService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis: Redis | None = None

    def _client(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(
                self.settings.redis_connection_url, decode_responses=True
            )
        return self._redis

    def _store_state(self, *, provider: str, state: str) -> None:
        self._client().setex(f"{OAUTH_STATE_PREFIX}{state}", OAUTH_STATE_TTL_SECONDS, provider)

    def _consume_state(self, *, provider: str, state: str | None) -> None:
        if not state:
            raise ValidationAppError("Missing OAuth state")
        key = f"{OAUTH_STATE_PREFIX}{state}"
        stored = self._client().get(key)
        self._client().delete(key)
        if stored != provider:
            raise UnauthorizedError("Invalid or expired OAuth state")

    def google_authorize_url(self, *, redirect_uri: str) -> tuple[str, str]:
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise AppError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
                code="oauth_not_configured",
                status_code=501,
            )
        state = secrets.token_urlsafe(24)
        self._store_state(provider="google", state=state)
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "include_granted_scopes": "true",
            "state": state,
            "prompt": "select_account",
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return url, state

    def github_authorize_url(self, *, redirect_uri: str) -> tuple[str, str]:
        if not self.settings.github_client_id or not self.settings.github_client_secret:
            raise AppError(
                "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
                code="oauth_not_configured",
                status_code=501,
            )
        state = secrets.token_urlsafe(24)
        self._store_state(provider="github", state=state)
        params = {
            "client_id": self.settings.github_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        return url, state

    def exchange(self, *, provider: str, code: str, state: str | None, redirect_uri: str) -> OAuthProfile:
        provider = provider.lower()
        if not code:
            raise ValidationAppError("Missing OAuth authorization code")
        self._consume_state(provider=provider, state=state)
        if provider == "google":
            return self._exchange_google(code=code, redirect_uri=redirect_uri)
        if provider == "github":
            return self._exchange_github(code=code, redirect_uri=redirect_uri)
        raise ValidationAppError("Unsupported OAuth provider")

    def _exchange_google(self, *, code: str, redirect_uri: str) -> OAuthProfile:
        with httpx.Client(timeout=20.0) as client:
            token_resp = client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code >= 400:
                logger.warning("google_token_exchange_failed", body=token_resp.text[:300])
                raise UnauthorizedError("Google OAuth token exchange failed")
            access = token_resp.json().get("access_token")
            if not access:
                raise UnauthorizedError("Google OAuth did not return an access token")

            userinfo = client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access}"},
            )
            userinfo.raise_for_status()
            data = userinfo.json()

        email = (data.get("email") or "").strip().lower()
        sub = str(data.get("sub") or "")
        if not email or not sub:
            raise ValidationAppError("Google account did not provide email")
        return OAuthProfile(
            provider="google",
            provider_user_id=sub,
            email=email,
            full_name=(data.get("name") or email.split("@")[0]).strip(),
            avatar_url=data.get("picture"),
            email_verified=bool(data.get("email_verified", True)),
        )

    def _exchange_github(self, *, code: str, redirect_uri: str) -> OAuthProfile:
        with httpx.Client(timeout=20.0) as client:
            token_resp = client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.settings.github_client_id,
                    "client_secret": self.settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            if token_resp.status_code >= 400:
                logger.warning("github_token_exchange_failed", body=token_resp.text[:300])
                raise UnauthorizedError("GitHub OAuth token exchange failed")
            access = token_resp.json().get("access_token")
            if not access:
                raise UnauthorizedError("GitHub OAuth did not return an access token")

            headers = {
                "Authorization": f"Bearer {access}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            user_resp = client.get("https://api.github.com/user", headers=headers)
            user_resp.raise_for_status()
            data = user_resp.json()
            emails_resp = client.get("https://api.github.com/user/emails", headers=headers)
            emails_resp.raise_for_status()
            emails = emails_resp.json() if isinstance(emails_resp.json(), list) else []

        email = ""
        verified = False
        for row in emails:
            if row.get("primary") and row.get("verified"):
                email = str(row.get("email") or "").lower()
                verified = True
                break
        if not email:
            for row in emails:
                if row.get("verified"):
                    email = str(row.get("email") or "").lower()
                    verified = True
                    break
        if not email:
            email = str(data.get("email") or "").lower()

        github_id = str(data.get("id") or "")
        if not email or not github_id:
            raise ValidationAppError(
                "GitHub account must have a public or verified email. Add one in GitHub settings."
            )
        return OAuthProfile(
            provider="github",
            provider_user_id=github_id,
            email=email,
            full_name=(data.get("name") or data.get("login") or email.split("@")[0]).strip(),
            avatar_url=data.get("avatar_url"),
            email_verified=verified or True,
        )
