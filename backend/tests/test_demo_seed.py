"""Smoke test for demo seed (Postgres)."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.db.demo_seed import seed_demo
from app.db.seed import seed
from app.models import Interview, StudyPlan, Submission, User, UserCompanyRoadmap
from app.models.enums import SubmissionStatus

REQUIRES_POSTGRES = pytest.mark.skipif(
    "postgresql" not in os.getenv("DATABASE_URL", ""),
    reason="Requires PostgreSQL",
)


@REQUIRES_POSTGRES
def test_demo_seed_idempotent() -> None:
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        seed(db)
        user1 = seed_demo(db)
        assert user1 is not None
        email = user1.email
        user2 = seed_demo(db)
        assert user2 is not None
        assert user2.email == email

        users = list(db.scalars(select(User).where(User.email == email)).all())
        assert len(users) == 1
        assert db.scalar(
            select(Interview).where(Interview.user_id == user1.id)
        ) is not None
        assert (
            db.scalar(
                select(Submission).where(
                    Submission.user_id == user1.id,
                    Submission.status == SubmissionStatus.ACCEPTED,
                )
            )
            is not None
        )
        assert db.scalar(select(StudyPlan).where(StudyPlan.user_id == user1.id)) is not None
        assert (
            db.scalar(
                select(UserCompanyRoadmap).where(UserCompanyRoadmap.user_id == user1.id)
            )
            is not None
        )
    finally:
        db.close()
