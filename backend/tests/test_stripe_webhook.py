"""Stripe webhook + billing sync tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.db.seed import seed
from app.main import create_app
from app.models import UserSubscription
from app.models.enums import PlanCode
from sqlalchemy import select

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


def _auth_user(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"stripe_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecurePass1"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Stripe User", "password": password},
    )
    assert reg.status_code == 201
    client.post("/api/v1/auth/verify-email", json={"token": reg.json()["debug_token"]})
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, me.json()["id"]


@REQUIRES_POSTGRES
def test_stripe_webhook_checkout_completed(client: TestClient) -> None:
    _, user_id = _auth_user(client)
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": user_id,
                "metadata": {"plan": "pro", "user_id": user_id},
                "customer": "cus_test",
                "subscription": "sub_test",
            }
        },
    }
    res = client.post("/api/v1/billing/webhook/stripe", json=event)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["received"] is True
    assert body["handled"] is True

    db = SessionLocal()
    try:
        row = db.scalar(
            select(UserSubscription).where(UserSubscription.user_id == UUID(user_id))
        )
        assert row is not None
        assert row.plan == PlanCode.PRO
        assert row.stripe_subscription_id == "sub_test"
    finally:
        db.close()


@REQUIRES_POSTGRES
def test_stripe_webhook_signature_when_configured(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    secret = "whsec_test_secret"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    get_settings.cache_clear()

    payload = json.dumps(
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_missing", "status": "canceled"}},
        }
    ).encode()
    timestamp = str(int(time.time()))
    signed = f"{timestamp}.{payload.decode()}".encode()
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={sig}"

    # Recreate client so settings reload
    fresh = TestClient(create_app())
    res = fresh.post(
        "/api/v1/billing/webhook/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "stripe-signature": header},
    )
    assert res.status_code == 200, res.text
    assert res.json()["handled"] is False
    get_settings.cache_clear()
