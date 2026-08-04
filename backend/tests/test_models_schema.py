"""Schema smoke tests — no live Postgres required."""

from app.database.base import Base
import app.models  # noqa: F401


EXPECTED_TABLES = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "sessions",
    "refresh_tokens",
    "email_verification_tokens",
    "password_reset_tokens",
    "resumes",
    "resume_analyses",
    "interviews",
    "questions",
    "answers",
    "feedback",
    "coding_problems",
    "submissions",
    "execution_results",
    "analytics",
    "achievements",
    "user_achievements",
    "notifications",
    "reports",
    "activity_logs",
    "study_plans",
    "study_plan_tasks",
    "coach_messages",
    "user_company_roadmaps",
    "user_subscriptions",
}


def test_all_expected_tables_are_registered() -> None:
    registered = set(Base.metadata.tables.keys())
    missing = EXPECTED_TABLES - registered
    assert not missing, f"Missing tables: {sorted(missing)}"


def test_users_email_is_unique() -> None:
    users = Base.metadata.tables["users"]
    email = users.c.email
    assert email.unique is True or any(
        getattr(c, "unique", False) and list(c.columns) == [email]
        for c in users.constraints
    )


def test_refresh_tokens_hash_is_unique() -> None:
    tokens = Base.metadata.tables["refresh_tokens"]
    assert tokens.c.token_hash.unique is True
