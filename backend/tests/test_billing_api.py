"""Billing API tests (Postgres)."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.db.seed import seed
from app.main import create_app

REQUIRES_POSTGRES = pytest.mark.skipif(
    "postgresql" not in os.getenv("DATABASE_URL", ""),
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


def _auth_headers(client: TestClient) -> dict[str, str]:
    email = f"bill_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Billing User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_plans_public_and_local_upgrade(client: TestClient) -> None:
    plans = client.get("/api/v1/billing/plans")
    assert plans.status_code == 200
    codes = [p["code"] for p in plans.json()]
    assert codes == ["free", "pro", "team"]

    headers = _auth_headers(client)
    me = client.get("/api/v1/billing/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["plan"] == "free"
    assert me.json()["billing_mode"] == "local"
    assert me.json()["entitlements"]["can_use_coach"] is False
    assert me.json()["entitlements"]["can_use_voice"] is False

    checkout = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan": "pro"},
    )
    assert checkout.status_code == 200, checkout.text
    body = checkout.json()
    assert body["mode"] == "local_activated"
    assert body["subscription"]["plan"] == "pro"
    assert body["subscription"]["entitlements"]["can_use_coach"] is True
    assert body["subscription"]["entitlements"]["can_use_voice"] is True

    # Voice interview allowed on Pro
    voice = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "voice", "question_count": 1},
    )
    assert voice.status_code == 201, voice.text


@REQUIRES_POSTGRES
def test_free_blocks_voice_and_coach(client: TestClient) -> None:
    headers = _auth_headers(client)
    blocked = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "voice", "question_count": 1},
    )
    assert blocked.status_code == 422

    coach = client.post(
        "/api/v1/coach/plans",
        headers=headers,
        json={"weeks": 1},
    )
    assert coach.status_code == 422

    # Text interviews still OK on free
    tech = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "technical", "question_count": 1},
    )
    assert tech.status_code == 201, tech.text
