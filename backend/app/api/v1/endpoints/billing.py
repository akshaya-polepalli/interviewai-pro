"""Billing and subscription endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status

from app.dependencies import DbSession, require_permissions
from app.models import User
from app.schemas.billing import (
    ActivatePlanRequest,
    CancelSubscriptionRequest,
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.billing_service import BillingService

router = APIRouter(prefix="/billing", tags=["Billing"])

BillingReader = Annotated[User, Depends(require_permissions("billing:read"))]
BillingWriter = Annotated[User, Depends(require_permissions("billing:write"))]


def _service(db: DbSession) -> BillingService:
    return BillingService(db)


@router.get("/plans", response_model=list[PlanResponse], summary="List subscription plans")
def list_plans(db: DbSession) -> list[PlanResponse]:
    # Public catalog — no auth required for pricing page visitors.
    return _service(db).list_plans()


@router.get("/me", response_model=SubscriptionResponse, summary="My subscription + entitlements")
def my_subscription(user: BillingReader, db: DbSession) -> SubscriptionResponse:
    return _service(db).get_subscription(user.id)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Start checkout (Stripe) or local-activate when no Stripe key",
)
def checkout(
    payload: CheckoutRequest,
    user: BillingWriter,
    db: DbSession,
) -> CheckoutResponse:
    return _service(db).checkout(user.id, payload)


@router.post(
    "/activate",
    response_model=SubscriptionResponse,
    summary="Locally activate a plan (demo / no Stripe)",
)
def activate_plan(
    payload: ActivatePlanRequest,
    user: BillingWriter,
    db: DbSession,
) -> SubscriptionResponse:
    return _service(db).activate_local(user.id, payload)


@router.post(
    "/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel paid plan (at period end or immediately)",
)
def cancel_plan(
    payload: CancelSubscriptionRequest,
    user: BillingWriter,
    db: DbSession,
) -> SubscriptionResponse:
    return _service(db).cancel(user.id, at_period_end=payload.at_period_end)


@router.post(
    "/webhook/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe webhook — verify signature and sync subscription",
)
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, Any]:
    from app.core.config import get_settings
    from app.core.exceptions import ValidationAppError

    settings = get_settings()
    payload = await request.body()
    sig = request.headers.get("stripe-signature") or ""

    if settings.stripe_webhook_secret:
        try:
            import hmac
            import hashlib
            import time

            # Lightweight Stripe signature verification (v1).
            elements = dict(
                part.split("=", 1) for part in sig.split(",") if "=" in part
            )
            timestamp = elements.get("t")
            v1 = elements.get("v1")
            if not timestamp or not v1:
                raise ValidationAppError("Invalid Stripe signature header")
            if abs(time.time() - int(timestamp)) > 300:
                raise ValidationAppError("Stripe webhook timestamp too old")
            signed = f"{timestamp}.{payload.decode('utf-8')}".encode()
            expected = hmac.new(
                settings.stripe_webhook_secret.encode(),
                signed,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, v1):
                raise ValidationAppError("Stripe signature mismatch")
        except ValidationAppError:
            raise
        except Exception as exc:
            raise ValidationAppError(f"Stripe signature verification failed: {exc}") from exc

    import json

    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValidationAppError("Invalid JSON webhook body") from exc

    result = _service(db).apply_stripe_event(event)
    return {"received": True, **result}
