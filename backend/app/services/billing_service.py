"""
Subscription billing service.

Local mode (default): activate/cancel plans without Stripe — great for demos.
Stripe mode: when STRIPE_SECRET_KEY is set, checkout creates a Checkout Session URL.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationAppError
from app.core.logging import get_logger
from app.models import Interview, Notification, UserSubscription
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    PlanCode,
    SubscriptionStatus,
)
from app.schemas.billing import (
    ActivatePlanRequest,
    CheckoutRequest,
    CheckoutResponse,
    EntitlementsResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.plan_catalog import PlanDef, get_plan, list_plans

logger = get_logger(__name__)


def _enum_val(value: object | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


class BillingService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.settings.stripe_secret_key.strip()) and not self.settings.billing_force_local

    def list_plans(self) -> list[PlanResponse]:
        return [self._plan_resp(p) for p in list_plans()]

    def get_subscription(self, user_id: UUID) -> SubscriptionResponse:
        sub = self._get_or_create(user_id)
        return self._sub_resp(sub)

    def checkout(self, user_id: UUID, payload: CheckoutRequest) -> CheckoutResponse:
        plan = self._require_paid_plan(payload.plan)
        if not self.stripe_enabled:
            # Demo / local path — activate immediately.
            sub = self._set_plan(user_id, plan.code, source="local_checkout")
            return CheckoutResponse(
                mode="local_activated",
                plan=plan.code,
                checkout_url=None,
                message=f"Local billing: activated {plan.name} (no Stripe key configured).",
                subscription=self._sub_resp(sub),
            )

        url = self._create_stripe_checkout(
            user_id=user_id,
            plan=plan,
            success_path=payload.success_path,
            cancel_path=payload.cancel_path,
        )
        return CheckoutResponse(
            mode="checkout_url",
            plan=plan.code,
            checkout_url=url,
            message="Redirect the browser to Stripe Checkout.",
            subscription=None,
        )

    def activate_local(self, user_id: UUID, payload: ActivatePlanRequest) -> SubscriptionResponse:
        if self.stripe_enabled and not self.settings.billing_force_local:
            raise ValidationAppError(
                "Stripe is configured — use checkout instead of local activate",
            )
        plan_code = payload.plan.value if isinstance(payload.plan, PlanCode) else str(payload.plan)
        if plan_code == PlanCode.FREE.value:
            sub = self._set_plan(user_id, PlanCode.FREE.value, source="local_activate")
            return self._sub_resp(sub)
        plan = self._require_paid_plan(payload.plan)
        sub = self._set_plan(user_id, plan.code, source="local_activate")
        return self._sub_resp(sub)

    def cancel(self, user_id: UUID, *, at_period_end: bool = True) -> SubscriptionResponse:
        sub = self._get_or_create(user_id)
        if _enum_val(sub.plan) == PlanCode.FREE.value:
            raise ValidationAppError("Free plan has nothing to cancel")

        if at_period_end:
            sub.cancel_at_period_end = True
            sub.extra = {**(sub.extra or {}), "cancel_requested_at": datetime.now(UTC).isoformat()}
            self.db.add(sub)
            self.db.commit()
            return self._sub_resp(sub)

        sub = self._set_plan(user_id, PlanCode.FREE.value, source="cancel_immediate")
        return self._sub_resp(sub)

    def assert_can_start_interview(self, user_id: UUID, *, voice: bool = False) -> None:
        ent = self.get_subscription(user_id).entitlements
        if voice and not ent.can_use_voice:
            raise ValidationAppError(
                "Voice interviews require Pro or Team. Upgrade on the Billing page."
            )
        if not ent.can_start_interview:
            raise ValidationAppError(
                "Monthly interview limit reached on Free. Upgrade to Pro for unlimited mocks."
            )

    def assert_can_use_coach(self, user_id: UUID) -> None:
        ent = self.get_subscription(user_id).entitlements
        if not ent.can_use_coach:
            raise ValidationAppError(
                "AI Coach requires Pro or Team. Upgrade on the Billing page."
            )

    def apply_stripe_event(self, event: dict) -> dict:
        """Apply a verified Stripe webhook event to local subscription state."""
        etype = event.get("type") or ""
        data = (event.get("data") or {}).get("object") or {}

        if etype == "checkout.session.completed":
            user_id = data.get("client_reference_id") or (data.get("metadata") or {}).get("user_id")
            plan = (data.get("metadata") or {}).get("plan") or "pro"
            if not user_id:
                return {"handled": False, "reason": "missing_user"}
            sub = self._set_plan(UUID(str(user_id)), plan, source="stripe_checkout")
            sub.stripe_customer_id = data.get("customer") or sub.stripe_customer_id
            sub.stripe_subscription_id = data.get("subscription") or sub.stripe_subscription_id
            self.db.add(sub)
            self.db.commit()
            return {"handled": True, "plan": plan, "user_id": str(user_id)}

        if etype in {"customer.subscription.updated", "customer.subscription.deleted"}:
            stripe_sub_id = data.get("id")
            status = data.get("status")
            row = None
            if stripe_sub_id:
                row = self.db.scalar(
                    select(UserSubscription).where(
                        UserSubscription.stripe_subscription_id == stripe_sub_id
                    )
                )
            if row is None:
                return {"handled": False, "reason": "subscription_not_found"}

            if etype == "customer.subscription.deleted" or status in {"canceled", "unpaid"}:
                row.plan = PlanCode.FREE
                row.status = SubscriptionStatus.CANCELED
                row.cancel_at_period_end = False
                row.current_period_end = None
            elif status == "active":
                row.status = SubscriptionStatus.ACTIVE
                meta = data.get("metadata") or {}
                if meta.get("plan") in {"pro", "team"}:
                    row.plan = PlanCode(meta["plan"])
            elif status == "past_due":
                row.status = SubscriptionStatus.PAST_DUE
            elif status == "trialing":
                row.status = SubscriptionStatus.TRIALING

            self.db.add(row)
            self.db.commit()
            return {"handled": True, "status": status, "user_id": str(row.user_id)}

        return {"handled": False, "reason": f"ignored:{etype}"}


    def _require_paid_plan(self, plan: PlanCode | str) -> PlanDef:
        code = plan.value if isinstance(plan, PlanCode) else str(plan)
        if code == PlanCode.FREE.value:
            raise ValidationAppError("Use cancel/downgrade to return to Free")
        defn = get_plan(code)
        if defn is None:
            raise ValidationAppError("Unknown plan")
        return defn

    def _get_or_create(self, user_id: UUID) -> UserSubscription:
        row = self.db.scalar(select(UserSubscription).where(UserSubscription.user_id == user_id))
        if row:
            return row
        row = UserSubscription(
            user_id=user_id,
            plan=PlanCode.FREE,
            status=SubscriptionStatus.ACTIVE,
            extra={"source": "auto_create"},
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _set_plan(self, user_id: UUID, plan_code: str, *, source: str) -> UserSubscription:
        sub = self._get_or_create(user_id)
        sub.plan = PlanCode(plan_code)
        sub.status = SubscriptionStatus.ACTIVE
        sub.cancel_at_period_end = False
        if plan_code == PlanCode.FREE.value:
            sub.current_period_end = None
            sub.stripe_subscription_id = None
        else:
            sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
            if not sub.stripe_customer_id and not self.stripe_enabled:
                sub.stripe_customer_id = f"cus_local_{uuid4().hex[:10]}"
                sub.stripe_subscription_id = f"sub_local_{uuid4().hex[:10]}"
        sub.extra = {**(sub.extra or {}), "source": source, "updated_via": source}
        self.db.add(sub)
        self.db.add(
            Notification(
                user_id=user_id,
                title=f"Plan updated: {plan_code}",
                body=f"Your InterviewAI Pro plan is now “{plan_code}”.",
                channel=NotificationChannel.IN_APP,
                status=NotificationStatus.SENT,
                payload={"type": "billing", "plan": plan_code},
                sent_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def _interviews_used_this_month(self, user_id: UUID) -> int:
        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Interview)
                .where(Interview.user_id == user_id, Interview.created_at >= start)
            )
            or 0
        )

    def _entitlements(self, sub: UserSubscription) -> EntitlementsResponse:
        plan_code = _enum_val(sub.plan) or PlanCode.FREE.value
        # Canceled / past_due fall back to free entitlements for gating.
        status = _enum_val(sub.status) or SubscriptionStatus.ACTIVE.value
        effective = plan_code
        if status in {SubscriptionStatus.CANCELED.value, SubscriptionStatus.PAST_DUE.value}:
            effective = PlanCode.FREE.value
        plan = get_plan(effective) or get_plan("free")
        assert plan is not None
        used = self._interviews_used_this_month(sub.user_id)
        limit = plan.interviews_per_month
        can_start = limit is None or used < limit
        return EntitlementsResponse(
            plan=plan.code,
            interviews_per_month=plan.interviews_per_month,
            interviews_used_this_month=used,
            voice_interviews=plan.voice_interviews,
            coach=plan.coach,
            reports=plan.reports,
            company_roadmaps=plan.company_roadmaps,
            priority_support=plan.priority_support,
            can_start_interview=can_start,
            can_use_voice=plan.voice_interviews,
            can_use_coach=plan.coach,
        )

    def _sub_resp(self, sub: UserSubscription) -> SubscriptionResponse:
        return SubscriptionResponse(
            id=sub.id,
            plan=_enum_val(sub.plan) or "free",
            status=_enum_val(sub.status) or "active",
            cancel_at_period_end=bool(sub.cancel_at_period_end),
            current_period_end=sub.current_period_end,
            stripe_customer_id=sub.stripe_customer_id,
            billing_mode="stripe" if self.stripe_enabled else "local",
            entitlements=self._entitlements(sub),
        )

    @staticmethod
    def _plan_resp(plan: PlanDef) -> PlanResponse:
        return PlanResponse(
            code=plan.code,
            name=plan.name,
            price_monthly_usd=plan.price_monthly_usd,
            blurb=plan.blurb,
            features=list(plan.features),
            interviews_per_month=plan.interviews_per_month,
            voice_interviews=plan.voice_interviews,
            coach=plan.coach,
            reports=plan.reports,
            company_roadmaps=plan.company_roadmaps,
            priority_support=plan.priority_support,
        )

    def _create_stripe_checkout(
        self,
        *,
        user_id: UUID,
        plan: PlanDef,
        success_path: str,
        cancel_path: str,
    ) -> str:
        price_id = (
            self.settings.stripe_price_pro
            if plan.code == "pro"
            else self.settings.stripe_price_team
        )
        if not price_id:
            raise ValidationAppError(
                f"Missing Stripe price id for {plan.code}. Set STRIPE_PRICE_PRO / STRIPE_PRICE_TEAM."
            )
        frontend = self.settings.frontend_url.rstrip("/")
        success_url = f"{frontend}{success_path}&session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend}{cancel_path}"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.stripe.com/v1/checkout/sessions",
                    headers={"Authorization": f"Bearer {self.settings.stripe_secret_key}"},
                    data={
                        "mode": "subscription",
                        "success_url": success_url,
                        "cancel_url": cancel_url,
                        "line_items[0][price]": price_id,
                        "line_items[0][quantity]": "1",
                        "client_reference_id": str(user_id),
                        "metadata[plan]": plan.code,
                        "metadata[user_id]": str(user_id),
                    },
                )
                resp.raise_for_status()
                url = resp.json().get("url")
                if not url:
                    raise ValidationAppError("Stripe did not return a checkout URL")
                return url
        except ValidationAppError:
            raise
        except Exception as exc:
            logger.exception("stripe_checkout_failed")
            raise ValidationAppError(f"Stripe checkout failed: {exc}") from exc
