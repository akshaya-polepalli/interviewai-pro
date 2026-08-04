"""Resume persistence helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Resume, ResumeAnalysis
from app.models.enums import ResumeStatus


class ResumeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, resume_id: UUID, user_id: UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.analysis))
            .where(
                Resume.id == resume_id,
                Resume.user_id == user_id,
                Resume.is_deleted.is_(False),
            )
        )

    def get_by_id(self, resume_id: UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .options(selectinload(Resume.analysis))
            .where(Resume.id == resume_id, Resume.is_deleted.is_(False))
        )

    def list_for_user(self, user_id: UUID) -> list[Resume]:
        return list(
            self.db.scalars(
                select(Resume)
                .options(selectinload(Resume.analysis))
                .where(Resume.user_id == user_id, Resume.is_deleted.is_(False))
                .order_by(Resume.created_at.desc())
            ).all()
        )

    def create(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.flush()
        return resume

    def save(self, resume: Resume) -> Resume:
        self.db.add(resume)
        self.db.flush()
        return resume

    def upsert_analysis(self, analysis: ResumeAnalysis) -> ResumeAnalysis:
        existing = self.db.scalar(
            select(ResumeAnalysis).where(ResumeAnalysis.resume_id == analysis.resume_id)
        )
        if existing:
            existing.ats_score = analysis.ats_score
            existing.keyword_match_score = analysis.keyword_match_score
            existing.matched_keywords = analysis.matched_keywords
            existing.missing_keywords = analysis.missing_keywords
            existing.suggestions = analysis.suggestions
            existing.section_scores = analysis.section_scores
            existing.model_provider = analysis.model_provider
            existing.model_name = analysis.model_name
            existing.raw_response = analysis.raw_response
            self.db.add(existing)
            self.db.flush()
            return existing
        self.db.add(analysis)
        self.db.flush()
        return analysis

    def count_for_user(self, user_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(Resume)
                .where(Resume.user_id == user_id, Resume.is_deleted.is_(False))
            )
            or 0
        )

    def set_status(self, resume: Resume, status: ResumeStatus) -> None:
        resume.status = status
        self.save(resume)
