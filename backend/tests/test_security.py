"""Unit tests for password hashing and JWT helpers."""

from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("SecurePass1")
    assert hashed != "SecurePass1"
    assert verify_password("SecurePass1", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token, expires = create_access_token(subject=user_id, extra_claims={"roles": ["candidate"]})
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert payload["roles"] == ["candidate"]
    assert expires.tzinfo is not None


def test_decode_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        decode_access_token("not.a.jwt")


def test_opaque_token_hash_is_stable() -> None:
    raw = generate_opaque_token()
    assert hash_token(raw) == hash_token(raw)
    assert hash_token(raw) != raw
