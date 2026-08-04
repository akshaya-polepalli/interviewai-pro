"""Coach / study plan API integration tests (Postgres)."""

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
    email = f"coach_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Coach User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    upgrade = client.post("/api/v1/billing/checkout", headers=headers, json={"plan": "pro"})
    assert upgrade.status_code == 200, upgrade.text
    return headers


@REQUIRES_POSTGRES
def test_insights_plan_tasks_and_ask(client: TestClient) -> None:
    headers = _auth_headers(client)

    insights = client.get("/api/v1/coach/insights", headers=headers)
    assert insights.status_code == 200, insights.text
    body = insights.json()
    assert "headline" in body
    assert isinstance(body["tips"], list)
    assert body["suggested_weeks"] >= 1

    created = client.post(
        "/api/v1/coach/plans",
        headers=headers,
        json={"weeks": 1, "focus_areas": ["coding", "interview"]},
    )
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["status"] == "active"
    assert plan["weeks"] == 1
    assert len(plan["tasks"]) == 7
    plan_id = plan["id"]
    task_id = plan["tasks"][0]["id"]

    listed = client.get("/api/v1/coach/plans", headers=headers)
    assert listed.status_code == 200
    assert any(p["id"] == plan_id for p in listed.json())

    patched = client.patch(
        f"/api/v1/coach/plans/{plan_id}/tasks/{task_id}",
        headers=headers,
        json={"is_done": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["done_count"] == 1
    assert patched.json()["tasks"][0]["is_done"] is True

    asked = client.post(
        "/api/v1/coach/ask",
        headers=headers,
        json={"message": "How should I plan my coding practice this week?"},
    )
    assert asked.status_code == 200, asked.text
    reply = asked.json()
    assert reply["reply"]["role"] == "assistant"
    assert len(reply["reply"]["content"]) > 10
    assert len(reply["history"]) >= 2

    messages = client.get("/api/v1/coach/messages", headers=headers)
    assert messages.status_code == 200
    assert len(messages.json()) >= 2

    notifs = client.get("/api/v1/notifications", headers=headers)
    assert notifs.status_code == 200
    assert any("Study plan ready" in n["title"] for n in notifs.json())

    archived = client.post(f"/api/v1/coach/plans/{plan_id}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
