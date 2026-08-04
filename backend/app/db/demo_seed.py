"""
Demo user + sample activity for portfolio walkthroughs (Module 14).

Idempotent: safe to re-run. Creates demo@interviewai.local with interviews,
coding submission, study plan, company roadmap enrollment, and analytics touch.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.db.seed import seed as base_seed
from app.models import (
    Answer,
    CodingProblem,
    Feedback,
    Interview,
    Notification,
    Question,
    Role,
    StudyPlan,
    StudyPlanTask,
    Submission,
    User,
    UserCompanyRoadmap,
    UserSubscription,
)
from app.models.enums import (
    DifficultyLevel,
    InterviewStatus,
    InterviewType,
    NotificationChannel,
    NotificationStatus,
    PlanCode,
    ProgrammingLanguage,
    QuestionCategory,
    RoadmapEnrollmentStatus,
    StudyPlanStatus,
    SubmissionStatus,
    SubscriptionStatus,
    TargetCompany,
    TargetRole,
    UserStatus,
)
from app.services.analytics_service import AnalyticsService

logger = structlog.get_logger(__name__)


def _ensure_demo_user(db: Session) -> User:
    settings = get_settings()
    email = (settings.seed_demo_email or "demo@interviewai.local").strip().lower()
    password = settings.seed_demo_password or "DemoPass1"
    name = settings.seed_demo_name or "Demo Candidate"

    candidate = db.scalar(select(Role).where(Role.name == "candidate"))
    if candidate is None:
        raise RuntimeError("candidate role missing — run app.db.seed first")

    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.full_name = name
        user.status = UserStatus.ACTIVE
        user.is_email_verified = True
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
        user.target_role = TargetRole.SOFTWARE_ENGINEER
        user.target_company = TargetCompany.GOOGLE
        user.hashed_password = hash_password(password)
        if candidate not in (user.roles or []):
            user.roles = list({*(user.roles or []), candidate})
        db.add(user)
        db.flush()
        logger.info("demo_user_updated", email=email)
        return user

    user = User(
        email=email,
        full_name=name,
        hashed_password=hash_password(password),
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        email_verified_at=datetime.now(UTC),
        target_role=TargetRole.SOFTWARE_ENGINEER,
        target_company=TargetCompany.GOOGLE,
        years_of_experience=3,
        bio="Portfolio demo account — explore interviews, coding, coach, and roadmaps.",
        roles=[candidate],
    )
    db.add(user)
    db.flush()
    logger.info("demo_user_created", email=email)
    return user


def _ensure_sample_interview(db: Session, user: User) -> None:
    existing = db.scalar(
        select(Interview).where(
            Interview.user_id == user.id,
            Interview.title == "Demo Technical Round",
        )
    )
    if existing:
        return

    started = datetime.now(UTC) - timedelta(days=2)
    interview = Interview(
        user_id=user.id,
        title="Demo Technical Round",
        interview_type=InterviewType.TECHNICAL,
        status=InterviewStatus.EVALUATED,
        difficulty=DifficultyLevel.MEDIUM,
        target_role=TargetRole.SOFTWARE_ENGINEER,
        target_company=TargetCompany.GOOGLE,
        started_at=started,
        completed_at=started + timedelta(minutes=42),
        duration_seconds=42 * 60,
        overall_score=Decimal("78.00"),
        summary="Solid coverage of caching and indexing with clear tradeoffs.",
        config={"source": "demo_seed", "mode": "text"},
    )
    db.add(interview)
    db.flush()

    prompts = [
        (
            "How would you design a rate limiter for a public API?",
            QuestionCategory.SYSTEM_DESIGN,
            [
                "I would use a token bucket in Redis per user and IP. "
                "Distributed nodes share counters with TTL for burst control. "
                "Idempotency keys protect retries after timeouts."
            ],
        ),
        (
            "Walk through indexing strategies for a hot PostgreSQL table.",
            QuestionCategory.DATABASES,
            [
                "Start with B-tree on filter columns, covering indexes for frequent "
                "projections, and EXPLAIN ANALYZE before adding more indexes. "
                "Avoid write amplification on rarely queried columns."
            ],
        ),
    ]
    for idx, (prompt, category, answers) in enumerate(prompts, start=1):
        q = Question(
            interview_id=interview.id,
            sequence=idx,
            category=category,
            difficulty=DifficultyLevel.MEDIUM,
            prompt=prompt,
            expected_points=["redis", "distributed", "tradeoffs"],
        )
        db.add(q)
        db.flush()
        db.add(
            Answer(
                question_id=q.id,
                user_id=user.id,
                answer_text=answers[0],
                time_spent_seconds=600,
                score=Decimal("76.00"),
            )
        )

    db.add(
        Feedback(
            interview_id=interview.id,
            overall_score=Decimal("78.00"),
            technical_score=Decimal("80.00"),
            communication_score=Decimal("74.00"),
            confidence_score=Decimal("72.00"),
            strengths=["Clear structure", "Mentions distributed constraints"],
            improvements=["Add concrete latency numbers", "Discuss failure modes earlier"],
            detailed_feedback=(
                "You explained Redis rate limiting well. Next: quantify SLOs and "
                "compare token bucket vs sliding window under burst traffic."
            ),
            model_provider="demo_seed",
            model_name="heuristic",
        )
    )


def _ensure_sample_submission(db: Session, user: User) -> None:
    problem = db.scalar(select(CodingProblem).where(CodingProblem.slug == "two-sum"))
    if problem is None:
        return
    existing = db.scalar(
        select(Submission).where(
            Submission.user_id == user.id,
            Submission.problem_id == problem.id,
            Submission.status == SubmissionStatus.ACCEPTED,
        )
    )
    if existing:
        return

    db.add(
        Submission(
            user_id=user.id,
            problem_id=problem.id,
            language=ProgrammingLanguage.PYTHON,
            source_code=(
                "def two_sum(nums, target):\n"
                "    seen = {}\n"
                "    for i, n in enumerate(nums):\n"
                "        need = target - n\n"
                "        if need in seen:\n"
                "            return [seen[need], i]\n"
                "        seen[n] = i\n"
                "    return []\n"
            ),
            status=SubmissionStatus.ACCEPTED,
            passed_tests=4,
            total_tests=4,
            runtime_ms=12,
            memory_kb=1024,
        )
    )


def _ensure_study_plan(db: Session, user: User) -> None:
    existing = db.scalar(
        select(StudyPlan).where(
            StudyPlan.user_id == user.id,
            StudyPlan.title == "Demo 2-week Google prep",
        )
    )
    if existing:
        return

    plan = StudyPlan(
        user_id=user.id,
        title="Demo 2-week Google prep",
        summary="Seeded plan highlighting coding + system design focus areas.",
        status=StudyPlanStatus.ACTIVE,
        weeks=2,
        focus_areas=["coding", "system_design", "interview"],
        model_provider="demo_seed",
    )
    db.add(plan)
    db.flush()
    tasks = [
        ("Day 1: Warm-up coding set", "coding", "/coding", True),
        ("Day 2: System design sketch", "system_design", "/interviews", False),
        ("Day 3: Technical mock", "interview", "/interviews", False),
    ]
    for i, (title, category, path, done) in enumerate(tasks, start=1):
        db.add(
            StudyPlanTask(
                plan_id=plan.id,
                sequence=i,
                day_offset=i - 1,
                title=title,
                description="Demo milestone — replace by generating a live plan in Coach.",
                category=category,
                estimated_minutes=35,
                resource_path=path,
                is_done=done,
            )
        )


def _ensure_roadmap(db: Session, user: User) -> None:
    existing = db.scalar(
        select(UserCompanyRoadmap).where(
            UserCompanyRoadmap.user_id == user.id,
            UserCompanyRoadmap.company == TargetCompany.GOOGLE,
        )
    )
    if existing:
        existing.status = RoadmapEnrollmentStatus.ACTIVE
        existing.manual_done = list(
            dict.fromkeys([*(existing.manual_done or []), "g_trees", "g_design"])
        )
        db.add(existing)
        return

    db.add(
        UserCompanyRoadmap(
            user_id=user.id,
            company=TargetCompany.GOOGLE,
            status=RoadmapEnrollmentStatus.ACTIVE,
            manual_done=["g_trees", "g_design"],
            notes="Demo enrollment for Google track.",
        )
    )


def _ensure_notification(db: Session, user: User) -> None:
    existing = db.scalar(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.title == "Welcome to the demo account",
        )
    )
    if existing:
        return
    db.add(
        Notification(
            user_id=user.id,
            title="Welcome to the demo account",
            body="Explore Dashboard, Interviews, Coding, Coach, Roadmaps, and Reports.",
            channel=NotificationChannel.IN_APP,
            status=NotificationStatus.SENT,
            payload={"type": "demo"},
            sent_at=datetime.now(UTC),
        )
    )


def _ensure_subscription(db: Session, user: User) -> None:
    existing = db.scalar(select(UserSubscription).where(UserSubscription.user_id == user.id))
    if existing:
        existing.plan = PlanCode.PRO
        existing.status = SubscriptionStatus.ACTIVE
        existing.cancel_at_period_end = False
        existing.extra = {**(existing.extra or {}), "source": "demo_seed"}
        db.add(existing)
        return
    db.add(
        UserSubscription(
            user_id=user.id,
            plan=PlanCode.PRO,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id=f"cus_demo_{user.id.hex[:8]}",
            stripe_subscription_id=f"sub_demo_{user.id.hex[:8]}",
            extra={"source": "demo_seed"},
        )
    )


def seed_demo(db: Session) -> User | None:
    settings = get_settings()
    if not settings.seed_demo_enabled:
        logger.info("demo_seed_skipped", reason="SEED_DEMO_ENABLED=false")
        return None

    user = _ensure_demo_user(db)
    _ensure_sample_interview(db, user)
    _ensure_sample_submission(db, user)
    _ensure_study_plan(db, user)
    _ensure_roadmap(db, user)
    _ensure_subscription(db, user)
    _ensure_notification(db, user)
    db.commit()

    AnalyticsService(db).recompute(user.id)
    logger.info(
        "demo_seed_complete",
        email=user.email,
        hint="Sign in with SEED_DEMO_EMAIL / SEED_DEMO_PASSWORD",
    )
    return user


def main() -> None:
    db = SessionLocal()
    try:
        base_seed(db)
        seed_demo(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
