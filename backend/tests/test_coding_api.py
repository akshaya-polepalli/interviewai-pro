"""Coding API integration tests (Postgres)."""

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
    email = f"code_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Coder", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_list_and_solve_two_sum(client: TestClient) -> None:
    headers = _auth_headers(client)
    listed = client.get("/api/v1/coding/problems", headers=headers)
    assert listed.status_code == 200, listed.text
    problems = listed.json()
    assert len(problems) >= 1
    two_sum = next(p for p in problems if p["slug"] == "two-sum")

    detail = client.get(f"/api/v1/coding/problems/{two_sum['id']}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert "hidden_tests" not in body
    assert body["public_tests"]

    source = """
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        need = target - n
        if need in seen:
            return [seen[need], i]
        seen[n] = i
    return []
"""
    submit = client.post(
        f"/api/v1/coding/problems/{two_sum['id']}/submissions",
        headers=headers,
        json={"source_code": source, "language": "python", "sync": True},
    )
    assert submit.status_code == 201, submit.text
    result = submit.json()
    assert result["status"] == "accepted"
    assert result["passed_tests"] == result["total_tests"]
    # Hidden cases redact expected/actual
    hidden = [r for r in result["execution_results"] if r["is_hidden"]]
    assert hidden
    assert all(r["expected_stdout"] is None for r in hidden)

    mine = client.get(
        "/api/v1/coding/submissions",
        headers=headers,
        params={"problem_id": two_sum["id"]},
    )
    assert mine.status_code == 200
    assert any(s["id"] == result["id"] for s in mine.json())
