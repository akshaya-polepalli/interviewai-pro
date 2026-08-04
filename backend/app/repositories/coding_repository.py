"""Coding problem and submission persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import CodingProblem, ExecutionResult, Submission


class CodingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_published(self) -> list[CodingProblem]:
        return list(
            self.db.scalars(
                select(CodingProblem)
                .where(CodingProblem.is_published.is_(True))
                .order_by(CodingProblem.difficulty, CodingProblem.title)
            ).all()
        )

    def get_by_id(self, problem_id: UUID) -> CodingProblem | None:
        return self.db.scalar(select(CodingProblem).where(CodingProblem.id == problem_id))

    def get_by_slug(self, slug: str) -> CodingProblem | None:
        return self.db.scalar(select(CodingProblem).where(CodingProblem.slug == slug))

    def create_submission(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.flush()
        return submission

    def save_submission(self, submission: Submission) -> Submission:
        self.db.add(submission)
        self.db.flush()
        return submission

    def get_submission_for_user(self, submission_id: UUID, user_id: UUID) -> Submission | None:
        return self.db.scalar(
            select(Submission)
            .options(selectinload(Submission.execution_results))
            .where(Submission.id == submission_id, Submission.user_id == user_id)
        )

    def list_submissions_for_user(
        self, user_id: UUID, problem_id: UUID | None = None
    ) -> list[Submission]:
        stmt = (
            select(Submission)
            .options(selectinload(Submission.execution_results))
            .where(Submission.user_id == user_id)
            .order_by(Submission.created_at.desc())
        )
        if problem_id is not None:
            stmt = stmt.where(Submission.problem_id == problem_id)
        return list(self.db.scalars(stmt.limit(50)).all())

    def replace_execution_results(
        self, submission_id: UUID, results: list[ExecutionResult]
    ) -> None:
        existing = list(
            self.db.scalars(
                select(ExecutionResult).where(ExecutionResult.submission_id == submission_id)
            ).all()
        )
        for row in existing:
            self.db.delete(row)
        for row in results:
            self.db.add(row)
        self.db.flush()
