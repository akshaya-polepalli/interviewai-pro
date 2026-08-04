"""
Auth API integration tests against live Postgres (Docker).

Skip automatically when DATABASE_URL is sqlite / unset for local unit runs.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.seed import seed
from app.database.session import SessionLocal
from app.main import create_app

DATABASE_URL = os.getenv("DATABASE_URL", "")
REQUIRES_POSTGRES = pytest.mark.skipif(
    "postgresql" not in DATABASE_URL and "postgres" not in os.getenv("POSTGRES_HOST", ""),
    reason="Auth integration tests require PostgreSQL",
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    return TestClient(create_app())


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


@REQUIRES_POSTGRES
def test_register_login_me_flow(client: TestClient) -> None:
    email = _unique_email()
    password = "SecurePass1"

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": password},
    )
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body.get("debug_token")

    verify = client.post("/api/v1/auth/verify-email", json={"token": body["debug_token"]})
    assert verify.status_code == 200
    assert verify.json()["is_email_verified"] is True

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert "candidate" in me.json()["roles"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    # Old refresh token must fail (rotation)
    reuse = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert reuse.status_code == 401


@REQUIRES_POSTGRES
def test_duplicate_register_conflict(client: TestClient) -> None:
    email = _unique_email()
    payload = {"email": email, "full_name": "Dup User", "password": "SecurePass1"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    again = client.post("/api/v1/auth/register", json=payload)
    assert again.status_code == 409
