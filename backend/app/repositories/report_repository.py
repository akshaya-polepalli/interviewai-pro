"""Report persistence helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Report


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID, limit: int = 50) -> list[Report]:
        return list(
            self.db.scalars(
                select(Report)
                .where(Report.user_id == user_id)
                .order_by(Report.created_at.desc())
                .limit(limit)
            ).all()
        )

    def get_for_user(self, report_id: UUID, user_id: UUID) -> Report | None:
        return self.db.scalar(
            select(Report).where(Report.id == report_id, Report.user_id == user_id)
        )

    def get_by_id(self, report_id: UUID) -> Report | None:
        return self.db.scalar(select(Report).where(Report.id == report_id))

    def create(self, report: Report) -> Report:
        self.db.add(report)
        self.db.flush()
        return report

    def save(self, report: Report) -> Report:
        self.db.add(report)
        self.db.flush()
        return report

    def delete(self, report: Report) -> None:
        self.db.delete(report)
        self.db.flush()
