"""Voice interview API tests (Postgres)."""

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
    email = f"voice_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Voice User", "password": password},
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
def test_voice_interview_with_transcript_and_audio(client: TestClient) -> None:
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "interview_type": "voice",
            "target_role": "software_engineer",
            "difficulty": "medium",
            "question_count": 2,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["interview_type"] == "voice"
    assert body["config"]["mode"] == "voice"
    assert len(body["questions"]) == 2
    interview_id = body["id"]
    q0 = body["questions"][0]

    # Minimal RIFF-ish bytes accepted as audio/wav-ish via octet-stream + .webm name
    fake_audio = b"RIFF" + (b"\x00" * 64) + b"WEBMFAKEAUDIOCONTENT"

    answered = client.post(
        f"/api/v1/interviews/{interview_id}/answers/voice",
        headers=headers,
        data={
            "question_id": str(q0["id"]),
            "transcript": (
                "In my last project I owned an API outage. Situation: latency spiked. "
                "Task: restore SLOs. Action: rolled back a bad cache key and added alerts. "
                "Result: p99 dropped under 200ms within an hour."
            ),
            "time_spent_seconds": "90",
        },
        files={"audio": ("answer.webm", fake_audio, "audio/webm")},
    )
    assert answered.status_code == 200, answered.text
    detail = answered.json()
    ans = detail["questions"][0]["answers"][0]
    assert ans["has_audio"] is True
    assert ans["transcript"]
    assert "outage" in (ans["answer_text"] or "").lower()

    audio = client.get(
        f"/api/v1/interviews/{interview_id}/answers/{ans['id']}/audio",
        headers=headers,
    )
    assert audio.status_code == 200
    assert audio.content.startswith(b"RIFF")

    # Text-only path (browser STT without clip)
    q1 = detail["questions"][1]
    text_only = client.post(
        f"/api/v1/interviews/{interview_id}/answers/voice",
        headers=headers,
        data={
            "question_id": str(q1["id"]),
            "transcript": "I would start by clarifying requirements, then sketch APIs and data model.",
            "time_spent_seconds": "45",
        },
    )
    assert text_only.status_code == 200, text_only.text

    done = client.post(
        f"/api/v1/interviews/{interview_id}/complete?evaluate=true&sync=true",
        headers=headers,
    )
    assert done.status_code == 200, done.text
    result = done.json()
    assert result.get("overall_score") is not None or result.get("status") in {
        "evaluated",
        "completed",
    }


@REQUIRES_POSTGRES
def test_voice_endpoint_rejects_text_interview(client: TestClient) -> None:
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={"interview_type": "technical", "question_count": 1},
    )
    assert created.status_code == 201
    interview_id = created.json()["id"]
    qid = created.json()["questions"][0]["id"]
    bad = client.post(
        f"/api/v1/interviews/{interview_id}/answers/voice",
        headers=headers,
        data={"question_id": str(qid), "transcript": "hello"},
    )
    assert bad.status_code == 422
