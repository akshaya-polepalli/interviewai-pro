"""OAuth service unit tests (mocked Redis / HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import UnauthorizedError
from app.services.oauth_service import OAuthService


def _settings(**kwargs) -> Settings:
    base = {
        "google_client_id": "g-id",
        "google_client_secret": "g-secret",
        "github_client_id": "gh-id",
        "github_client_secret": "gh-secret",
        "redis_url": "redis://localhost:6379/0",
    }
    base.update(kwargs)
    return Settings(**base)


def test_google_authorize_stores_state() -> None:
    svc = OAuthService(_settings())
    fake_redis = MagicMock()
    svc._redis = fake_redis
    url, state = svc.google_authorize_url(redirect_uri="http://localhost:8000/cb")
    assert "accounts.google.com" in url
    assert state
    fake_redis.setex.assert_called_once()


def test_consume_state_rejects_mismatch() -> None:
    svc = OAuthService(_settings())
    fake_redis = MagicMock()
    fake_redis.get.return_value = "github"
    svc._redis = fake_redis
    with pytest.raises(UnauthorizedError):
        svc._consume_state(provider="google", state="abc")


def test_exchange_google_profile() -> None:
    svc = OAuthService(_settings())
    fake_redis = MagicMock()
    fake_redis.get.return_value = "google"
    svc._redis = fake_redis

    token_resp = MagicMock()
    token_resp.status_code = 200
    token_resp.json.return_value = {"access_token": "atok"}

    user_resp = MagicMock()
    user_resp.raise_for_status = MagicMock()
    user_resp.json.return_value = {
        "sub": "g-sub-1",
        "email": "g@example.com",
        "email_verified": True,
        "name": "G User",
        "picture": "https://example.com/a.png",
    }

    with patch("app.services.oauth_service.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.post.return_value = token_resp
        client.get.return_value = user_resp
        client_cls.return_value = client

        profile = svc.exchange(
            provider="google",
            code="code",
            state="st",
            redirect_uri="http://localhost/cb",
        )

    assert profile.provider == "google"
    assert profile.provider_user_id == "g-sub-1"
    assert profile.email == "g@example.com"
