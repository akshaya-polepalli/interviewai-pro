"""Static SaaS plan catalog and entitlements."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import PlanCode


@dataclass(frozen=True)
class PlanDef:
    code: str
    name: str
    price_monthly_usd: int
    blurb: str
    features: tuple[str, ...]
    interviews_per_month: int | None  # None = unlimited
    voice_interviews: bool
    coach: bool
    reports: bool
    company_roadmaps: bool
    priority_support: bool


PLANS: dict[str, PlanDef] = {
    PlanCode.FREE.value: PlanDef(
        code="free",
        name="Free",
        price_monthly_usd=0,
        blurb="Start practicing with core prep tools.",
        features=(
            "3 mock interviews / month",
            "Coding lab access",
            "Resume ATS scoring",
            "Basic analytics",
        ),
        interviews_per_month=3,
        voice_interviews=False,
        coach=False,
        reports=True,
        company_roadmaps=True,
        priority_support=False,
    ),
    PlanCode.PRO.value: PlanDef(
        code="pro",
        name="Pro",
        price_monthly_usd=29,
        blurb="Unlimited practice for serious candidates.",
        features=(
            "Unlimited interviews (text + voice)",
            "AI coach & study plans",
            "Company roadmaps",
            "PDF reports",
            "Priority evaluation queue",
        ),
        interviews_per_month=None,
        voice_interviews=True,
        coach=True,
        reports=True,
        company_roadmaps=True,
        priority_support=False,
    ),
    PlanCode.TEAM.value: PlanDef(
        code="team",
        name="Team",
        price_monthly_usd=99,
        blurb="For bootcamps and hiring cohorts.",
        features=(
            "Everything in Pro",
            "Shared admin analytics",
            "Priority support",
            "Seat-ready for multi-user orgs",
        ),
        interviews_per_month=None,
        voice_interviews=True,
        coach=True,
        reports=True,
        company_roadmaps=True,
        priority_support=True,
    ),
}


def get_plan(code: str) -> PlanDef | None:
    return PLANS.get(code.lower().strip())


def list_plans() -> list[PlanDef]:
    return [PLANS["free"], PLANS["pro"], PLANS["team"]]
