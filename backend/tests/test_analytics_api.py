"""Analytics API tests (Postgres)."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.seed import seed
from app.database.session import SessionLocal
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
    email = f"an_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Analytics User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_analytics_refresh_and_achievements(client: TestClient) -> None:
    headers = _auth_headers(client)

    # Create + evaluate a quick behavioral interview to generate progress
    created = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "behavioral", "question_count": 1},
    )
    assert created.status_code == 201
    interview_id = created.json()["id"]
    qid = created.json()["questions"][0]["id"]
    client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        headers=headers,
        json={
            "question_id": qid,
            "answer_text": (
                "Situation: We missed a deadline. Task: Recover trust. "
                "Action: I owned the miss and shipped a fix. Result: We improved delivery by 20%."
            ),
        },
    )
    done = client.post(
        f"/api/v1/interviews/{interview_id}/complete?evaluate=true&sync=true",
        headers=headers,
    )
    assert done.status_code == 200

    analytics = client.get("/api/v1/analytics/me?refresh=true", headers=headers)
    assert analytics.status_code == 200, analytics.text
    body = analytics.json()
    assert body["analytics"]["completed_interviews"] >= 1
    assert body["analytics"]["skill_radar"] is not None
    assert isinstance(body["analytics"]["roadmap"], list)
    assert any(a["code"] == "first_interview" and a["unlocked"] for a in body["achievements"])

    achievements = client.get("/api/v1/analytics/achievements", headers=headers)
    assert achievements.status_code == 200
    assert len(achievements.json()) >= 5
