"""Resume API integration tests (Postgres)."""

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
    email = f"resume_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Resume User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@REQUIRES_POSTGRES
def test_upload_analyze_list_delete_resume(client: TestClient) -> None:
    headers = _auth_headers(client)
    content = b"""
Alex Engineer
alex@example.com
Summary
Full stack developer focused on React and FastAPI.
Experience
- Developed React dashboards and Python APIs
- Used PostgreSQL, Docker, and AWS
Skills
Python, JavaScript, React, FastAPI, SQL, Docker, AWS, testing
"""
    files = {"file": ("resume.txt", content, "text/plain")}
    data = {"analyze": "true", "sync": "true", "target_role": "full_stack_engineer"}
    upload = client.post("/api/v1/resumes", headers=headers, files=files, data=data)
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["status"] == "analyzed"
    assert body["analysis"] is not None
    assert float(body["analysis"]["ats_score"]) > 0
    resume_id = body["resume_id"]

    listed = client.get("/api/v1/resumes", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == resume_id for item in listed.json())

    detail = client.get(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["raw_text_preview"]

    download = client.get(f"/api/v1/resumes/{resume_id}/download", headers=headers)
    assert download.status_code == 200
    assert b"Alex Engineer" in download.content

    deleted = client.delete(f"/api/v1/resumes/{resume_id}", headers=headers)
    assert deleted.status_code == 200
