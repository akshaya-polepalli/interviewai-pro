"""Reports API integration tests (Postgres)."""

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
    email = f"rp_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Report User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_generate_download_and_notify(client: TestClient) -> None:
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/reports",
        headers=headers,
        json={"report_type": "weekly_progress", "format": "pdf", "sync": True},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "ready"
    assert body["has_file"] is True
    assert body["content_type"] == "application/pdf"
    report_id = body["id"]

    download = client.get(f"/api/v1/reports/{report_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    assert "pdf" in (download.headers.get("content-type") or "").lower()

    listed = client.get("/api/v1/reports", headers=headers)
    assert listed.status_code == 200
    assert any(r["id"] == report_id for r in listed.json())

    notifs = client.get("/api/v1/notifications", headers=headers)
    assert notifs.status_code == 200
    assert any("Report ready" in n["title"] for n in notifs.json())

    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=headers)
    assert deleted.status_code == 200
