"""Company roadmap API tests (Postgres)."""

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
    email = f"rm_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Roadmap User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_list_enroll_toggle_archive(client: TestClient) -> None:
    headers = _auth_headers(client)

    catalog = client.get("/api/v1/roadmaps", headers=headers)
    assert catalog.status_code == 200, catalog.text
    companies = [t["company"] for t in catalog.json()]
    assert "google" in companies
    assert "amazon" in companies

    detail = client.get("/api/v1/roadmaps/google", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["enrolled"] is False
    assert len(detail.json()["milestones"]) >= 4

    enrolled = client.post(
        "/api/v1/roadmaps/enroll",
        headers=headers,
        json={"company": "google"},
    )
    assert enrolled.status_code == 201, enrolled.text
    body = enrolled.json()
    assert body["enrolled"] is True
    assert body["company"] == "google"
    mid = next(m["id"] for m in body["milestones"] if not m["auto_rule"])

    toggled = client.post(
        f"/api/v1/roadmaps/google/milestones",
        headers=headers,
        json={"milestone_id": mid, "is_done": True},
    )
    assert toggled.status_code == 200, toggled.text
    assert any(m["id"] == mid and m["done"] for m in toggled.json()["milestones"])
    assert toggled.json()["done_count"] >= 1

    archived = client.post("/api/v1/roadmaps/google/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["enrolled"] is False
    assert archived.json()["status"] == "archived"


@REQUIRES_POSTGRES
def test_unknown_company_404(client: TestClient) -> None:
    headers = _auth_headers(client)
    resp = client.get("/api/v1/roadmaps/not-a-company", headers=headers)
    assert resp.status_code == 404
