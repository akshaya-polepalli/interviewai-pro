"""Interview API integration tests (Postgres)."""

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
    email = f"iv_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Interview User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_technical_interview_flow(client: TestClient) -> None:
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "interview_type": "technical",
            "target_role": "backend_engineer",
            "target_company": "amazon",
            "difficulty": "medium",
            "question_count": 3,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert len(body["questions"]) == 3
    interview_id = body["id"]
    q0 = body["questions"][0]

    started = client.post(f"/api/v1/interviews/{interview_id}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"

    answer = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        headers=headers,
        json={
            "question_id": q0["id"],
            "answer_text": (
                "I would use Redis with a token bucket algorithm per user and per IP. "
                "For distributed nodes, a central Redis counter with TTL handles burst limits. "
                "Retries after timeout need idempotency keys so duplicate charges never happen. "
                "I monitor 429 rates and p99 latency."
            ),
            "time_spent_seconds": 120,
        },
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["answered_count"] >= 1

    # Answer remaining briefly so evaluation has coverage
    for q in body["questions"][1:]:
        client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={
                "question_id": q["id"],
                "answer_text": (
                    "I would start with EXPLAIN ANALYZE, add covering indexes carefully, "
                    "and avoid write amplification. For example I reduced query time by 40%."
                ),
            },
        )

    done = client.post(
        f"/api/v1/interviews/{interview_id}/complete?evaluate=true&sync=true",
        headers=headers,
    )
    assert done.status_code == 200, done.text
    result = done.json()
    assert result["status"] == "evaluated"
    assert result["overall_score"] is not None
    assert float(result["overall_score"]) > 0

    detail = client.get(f"/api/v1/interviews/{interview_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["feedback"] is not None
    assert detail.json()["feedback"]["strengths"]

    listed = client.get("/api/v1/interviews", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == interview_id for item in listed.json())


@REQUIRES_POSTGRES
def test_behavioral_interview_star_scoring(client: TestClient) -> None:
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "behavioral", "question_count": 2},
    )
    assert created.status_code == 201
    interview_id = created.json()["id"]
    questions = created.json()["questions"]

    star_answer = (
        "Situation: At my previous job our release failed on Friday. "
        "Task: I needed to restore service and prevent a repeat. "
        "Action: I led the rollback, wrote a postmortem, and added a canary check. "
        "Result: We reduced incident time by 50% and shipped a safer pipeline."
    )
    for q in questions:
        resp = client.post(
            f"/api/v1/interviews/{interview_id}/answers",
            headers=headers,
            json={"question_id": q["id"], "answer_text": star_answer},
        )
        assert resp.status_code == 200

    done = client.post(
        f"/api/v1/interviews/{interview_id}/complete?evaluate=true&sync=true",
        headers=headers,
    )
    assert done.status_code == 200
    detail = client.get(f"/api/v1/interviews/{interview_id}", headers=headers).json()
    assert detail["feedback"]["star_method_score"] is not None
    assert float(detail["feedback"]["star_method_score"]) >= 50
