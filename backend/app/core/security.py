"""
Security primitives: password hashing, JWT access tokens, opaque token hashing.

Industry rules this module encodes:
1. Never store plaintext passwords — bcrypt (slow hash) with automatic salt.
2. Access tokens are short-lived JWTs (stateless authorization).
3. Refresh tokens are long opaque secrets — store only SHA-256 hashes.
4. Always compare hashes with constant-time helpers where applicable.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import Settings, get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    *,
    subject: str | UUID,
    settings: Settings | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """
    Create a signed JWT access token.

    Returns (token, expires_at).
    """
    cfg = settings or get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=cfg.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, cfg.secret_key, algorithm=cfg.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    cfg = settings or get_settings()
    try:
        payload = jwt.decode(token, cfg.secret_key, algorithms=[cfg.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise ValueError("Invalid token type")
    return payload


def generate_opaque_token(nbytes: int = 32) -> str:
    """Cryptographically strong URL-safe token for refresh / email / reset."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw_token: str) -> str:
    """SHA-256 hex digest — irreversible storage form for opaque tokens."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
