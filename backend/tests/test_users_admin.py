"""User profile + admin API integration tests (Postgres)."""

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
    "postgresql" not in DATABASE_URL,
    reason="Requires PostgreSQL",
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


def _register_and_login(client: TestClient) -> dict:
    email = f"m4_{uuid.uuid4().hex[:10]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Module Four", "password": password},
    )
    assert reg.status_code == 201
    token = reg.json()["debug_token"]
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()


@REQUIRES_POSTGRES
def test_profile_update_and_sessions(client: TestClient) -> None:
    tokens = _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert "users:write" in me.json()["permissions"]

    updated = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "Updated Name",
            "bio": "Backend engineer",
            "target_role": "backend_engineer",
            "target_company": "google",
            "years_of_experience": 3,
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["full_name"] == "Updated Name"
    assert body["target_role"] == "backend_engineer"
    assert body["years_of_experience"] == 3

    sessions = client.get("/api/v1/users/me/sessions", headers=headers)
    assert sessions.status_code == 200
    assert len(sessions.json()) >= 1


@REQUIRES_POSTGRES
def test_admin_stats_and_user_list(client: TestClient) -> None:
    settings = get_settings()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.seed_admin_email,
            "password": settings.seed_admin_password,
        },
    )
    assert login.status_code == 200, login.text
    assert "admin" in login.json()["user"]["roles"]
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    stats = client.get("/api/v1/admin/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    assert stats.json()["total_users"] >= 1

    users = client.get("/api/v1/admin/users?page=1&page_size=10", headers=headers)
    assert users.status_code == 200
    assert "items" in users.json()

    roles = client.get("/api/v1/admin/roles", headers=headers)
    assert roles.status_code == 200
    assert any(r["name"] == "admin" for r in roles.json())


@REQUIRES_POSTGRES
def test_non_admin_cannot_access_admin(client: TestClient) -> None:
    tokens = _register_and_login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    denied = client.get("/api/v1/admin/stats", headers=headers)
    assert denied.status_code == 403
