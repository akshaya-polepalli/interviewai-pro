"""Billing request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PlanCode


class PlanResponse(BaseModel):
    code: str
    name: str
    price_monthly_usd: int
    blurb: str
    features: list[str]
    interviews_per_month: int | None = None
    voice_interviews: bool
    coach: bool
    reports: bool
    company_roadmaps: bool
    priority_support: bool


class EntitlementsResponse(BaseModel):
    plan: str
    interviews_per_month: int | None = None
    interviews_used_this_month: int = 0
    voice_interviews: bool
    coach: bool
    reports: bool
    company_roadmaps: bool
    priority_support: bool
    can_start_interview: bool = True
    can_use_voice: bool = False
    can_use_coach: bool = False


class SubscriptionResponse(BaseModel):
    id: UUID | None = None
    plan: str
    status: str
    cancel_at_period_end: bool = False
    current_period_end: datetime | None = None
    stripe_customer_id: str | None = None
    billing_mode: str  # local | stripe
    entitlements: EntitlementsResponse


class CheckoutRequest(BaseModel):
    plan: PlanCode = PlanCode.PRO
    success_path: str = Field(default="/billing?success=1", max_length=255)
    cancel_path: str = Field(default="/billing?canceled=1", max_length=255)


class CheckoutResponse(BaseModel):
    mode: str  # local_activated | checkout_url
    plan: str
    checkout_url: str | None = None
    message: str
    subscription: SubscriptionResponse | None = None


class ActivatePlanRequest(BaseModel):
    plan: PlanCode = PlanCode.PRO


class CancelSubscriptionRequest(BaseModel):
    at_period_end: bool = True
