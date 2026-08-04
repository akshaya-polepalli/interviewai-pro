"""
Downloadable progress reports.

Builds a structured payload from analytics + domain tables, then stores
JSON or Markdown in object storage. Creates an in-app notification when ready.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models import Interview, Notification, Report, Resume, User
from app.models.enums import (
    NotificationChannel,
    NotificationStatus,
    ReportStatus,
    ReportType,
)
from app.repositories.report_repository import ReportRepository
from app.schemas.reports import (
    CreateReportRequest,
    ReportAcceptedResponse,
    ReportDetailResponse,
    ReportResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.pdf_report import build_progress_pdf
from app.services.storage_service import StorageService

logger = get_logger(__name__)


def _enum_val(value: object | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def to_report_response(report: Report) -> ReportResponse:
    return ReportResponse(
        id=report.id,
        report_type=_enum_val(report.report_type) or "weekly_progress",
        status=_enum_val(report.status) or "pending",
        title=report.title,
        content_type=report.content_type,
        ready_at=report.ready_at,
        error_message=report.error_message,
        created_at=report.created_at,
        updated_at=report.updated_at,
        has_file=bool(report.storage_key),
    )


def to_detail(report: Report) -> ReportDetailResponse:
    base = to_report_response(report)
    return ReportDetailResponse(**base.model_dump(), payload=report.payload)


class ReportService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = ReportRepository(db)
        self.storage = StorageService(self.settings)
        self.analytics = AnalyticsService(db)

    def list_mine(self, user_id: UUID) -> list[ReportResponse]:
        return [to_report_response(r) for r in self.repo.list_for_user(user_id)]

    def get_mine(self, user_id: UUID, report_id: UUID) -> ReportDetailResponse:
        report = self.repo.get_for_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        return to_detail(report)

    def create(
        self, user_id: UUID, payload: CreateReportRequest
    ) -> ReportAcceptedResponse | ReportDetailResponse:
        title = payload.title or self._default_title(payload.report_type)
        report = Report(
            user_id=user_id,
            report_type=payload.report_type,
            status=ReportStatus.PENDING,
            title=title,
            payload={
                "format": payload.format,
                "interview_id": str(payload.interview_id) if payload.interview_id else None,
                "resume_id": str(payload.resume_id) if payload.resume_id else None,
            },
        )
        self.repo.create(report)
        self.db.commit()

        if not payload.sync:
            from app.workers.tasks import generate_report_task

            generate_report_task.delay(str(report.id))
            return ReportAcceptedResponse(
                report_id=report.id,
                status=ReportStatus.PENDING.value,
                message="Report generation queued",
            )

        self.process_report(report.id)
        self.db.expire_all()
        fresh = self.repo.get_for_user(report.id, user_id)
        assert fresh is not None
        return to_detail(fresh)

    def process_report(self, report_id: UUID) -> Report:
        report = self.repo.get_by_id(report_id)
        if report is None:
            raise NotFoundError("Report not found")

        report.status = ReportStatus.GENERATING
        self.repo.save(report)
        self.db.commit()

        try:
            fmt = "pdf"
            interview_id = None
            resume_id = None
            if isinstance(report.payload, dict):
                fmt = report.payload.get("format") or "pdf"
                interview_id = report.payload.get("interview_id")
                resume_id = report.payload.get("resume_id")

            data = self._build_payload(
                user_id=report.user_id,
                report_type=report.report_type,
                interview_id=UUID(interview_id) if interview_id else None,
                resume_id=UUID(resume_id) if resume_id else None,
            )
            data["_export_format"] = fmt

            if fmt == "json":
                body = json.dumps(data, indent=2, default=str).encode("utf-8")
                content_type = "application/json"
                ext = "json"
            elif fmt == "markdown":
                body = self._to_markdown(report.title, data).encode("utf-8")
                content_type = "text/markdown; charset=utf-8"
                ext = "md"
            else:
                body = build_progress_pdf(title=report.title, data=data)
                content_type = "application/pdf"
                ext = "pdf"

            key = self.storage.build_report_key(
                user_id=str(report.user_id),
                report_id=str(report.id),
                ext=ext,
            )
            self.storage.save_bytes(key=key, data=body, content_type=content_type)

            report.storage_key = key
            report.content_type = content_type
            report.payload = data
            report.status = ReportStatus.READY
            report.ready_at = datetime.now(UTC)
            report.error_message = None
            self.repo.save(report)
            self._notify_ready(report)
            self.db.commit()
            return report
        except Exception as exc:
            logger.exception("report_generation_failed", report_id=str(report_id))
            report.status = ReportStatus.FAILED
            report.error_message = str(exc)[:1000]
            self.repo.save(report)
            self.db.commit()
            raise

    def download(self, user_id: UUID, report_id: UUID) -> tuple[bytes, str, str]:
        report = self.repo.get_for_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        if _enum_val(report.status) != ReportStatus.READY.value or not report.storage_key:
            raise ValidationAppError("Report is not ready for download")
        data = self.storage.read_bytes(key=report.storage_key)
        ctype = report.content_type or "application/octet-stream"
        if ctype.startswith("application/pdf"):
            ext = "pdf"
        elif ctype.startswith("application/json"):
            ext = "json"
        else:
            ext = "md"
        filename = f"{report.title.replace(' ', '_').lower()}.{ext}"
        return data, ctype, filename

    def delete(self, user_id: UUID, report_id: UUID) -> None:
        report = self.repo.get_for_user(report_id, user_id)
        if report is None:
            raise NotFoundError("Report not found")
        if report.storage_key:
            try:
                self.storage.delete(key=report.storage_key)
            except Exception:
                logger.exception("report_file_delete_failed", key=report.storage_key)
        self.repo.delete(report)
        self.db.commit()

    def _build_payload(
        self,
        *,
        user_id: UUID,
        report_type: ReportType | str,
        interview_id: UUID | None,
        resume_id: UUID | None,
    ) -> dict:
        rtype = _enum_val(report_type) or ReportType.WEEKLY_PROGRESS.value
        user = self.db.get(User, user_id)
        bundle = self.analytics.get_bundle(user_id, refresh=True)
        analytics = bundle.analytics.model_dump(mode="json")
        achievements = [a.model_dump(mode="json") for a in bundle.achievements if a.unlocked]

        base = {
            "generated_at": datetime.now(UTC).isoformat(),
            "report_type": rtype,
            "user": {
                "id": str(user_id),
                "email": user.email if user else None,
                "full_name": user.full_name if user else None,
            },
            "analytics": analytics,
            "unlocked_achievements": achievements,
        }

        if rtype == ReportType.INTERVIEW_SUMMARY.value:
            if interview_id is None:
                raise ValidationAppError("interview_id is required for interview_summary")
            interview = self.db.scalar(
                select(Interview)
                .options(
                    selectinload(Interview.feedback),
                    selectinload(Interview.questions),
                )
                .where(Interview.id == interview_id, Interview.user_id == user_id)
            )
            if interview is None:
                raise NotFoundError("Interview not found")
            base["interview"] = {
                "id": str(interview.id),
                "title": interview.title,
                "type": _enum_val(interview.interview_type),
                "status": _enum_val(interview.status),
                "overall_score": str(interview.overall_score)
                if interview.overall_score is not None
                else None,
                "summary": interview.summary,
                "feedback": {
                    "strengths": interview.feedback.strengths if interview.feedback else None,
                    "improvements": interview.feedback.improvements if interview.feedback else None,
                    "detailed_feedback": interview.feedback.detailed_feedback
                    if interview.feedback
                    else None,
                }
                if interview.feedback
                else None,
                "question_count": len(interview.questions or []),
            }
        elif rtype == ReportType.RESUME_ATS.value:
            if resume_id is None:
                # latest resume with analysis
                resume = self.db.scalar(
                    select(Resume)
                    .options(selectinload(Resume.analysis))
                    .where(Resume.user_id == user_id, Resume.is_deleted.is_(False))
                    .order_by(Resume.created_at.desc())
                    .limit(1)
                )
            else:
                resume = self.db.scalar(
                    select(Resume)
                    .options(selectinload(Resume.analysis))
                    .where(
                        Resume.id == resume_id,
                        Resume.user_id == user_id,
                        Resume.is_deleted.is_(False),
                    )
                )
            if resume is None:
                raise NotFoundError("Resume not found")
            analysis = resume.analysis
            base["resume"] = {
                "id": str(resume.id),
                "filename": resume.original_filename,
                "ats_score": str(analysis.ats_score) if analysis and analysis.ats_score is not None else None,
                "matched_keywords": analysis.matched_keywords if analysis else None,
                "missing_keywords": analysis.missing_keywords if analysis else None,
                "suggestions": analysis.suggestions if analysis else None,
            }
        elif rtype == ReportType.ROADMAP.value:
            base["focus"] = "roadmap"
        else:
            # weekly / monthly / default — analytics already included
            base["focus"] = "progress"

        return base

    def _to_markdown(self, title: str, data: dict) -> str:
        user = data.get("user") or {}
        analytics = data.get("analytics") or {}
        radar = analytics.get("skill_radar") or {}
        roadmap = analytics.get("roadmap") or []
        lines = [
            f"# {title}",
            "",
            f"_Generated {data.get('generated_at')}_",
            "",
            f"**Candidate:** {user.get('full_name') or '—'} ({user.get('email') or '—'})",
            "",
            "## Snapshot",
            f"- Interviews completed: {analytics.get('completed_interviews', 0)}",
            f"- Average interview score: {analytics.get('average_score') or '—'}",
            f"- Coding accepted: {analytics.get('coding_accepted', 0)}/"
            f"{analytics.get('coding_submissions', 0)}",
            f"- Current streak: {analytics.get('current_streak_days', 0)} days",
            f"- Latest ATS: {analytics.get('latest_ats_score') or '—'}",
            "",
            "## Skill radar",
        ]
        for key in ("technical", "behavioral", "communication", "coding", "resume"):
            lines.append(f"- {key.title()}: {radar.get(key, 0)}")
        lines.extend(["", "## Roadmap"])
        for item in roadmap:
            mark = "x" if item.get("done") else " "
            lines.append(f"- [{mark}] {item.get('title')}")
        unlocked = data.get("unlocked_achievements") or []
        lines.extend(["", "## Achievements unlocked"])
        if unlocked:
            for a in unlocked:
                lines.append(f"- {a.get('title')} (+{a.get('points', 0)} pts)")
        else:
            lines.append("- None yet")

        if data.get("interview"):
            iv = data["interview"]
            lines.extend(
                [
                    "",
                    "## Interview summary",
                    f"- Title: {iv.get('title')}",
                    f"- Type: {iv.get('type')}",
                    f"- Score: {iv.get('overall_score') or '—'}",
                    "",
                    iv.get("summary") or "",
                ]
            )
            fb = iv.get("feedback") or {}
            if fb.get("strengths"):
                lines.extend(["", "### Strengths"])
                lines.extend([f"- {s}" for s in fb["strengths"]])
            if fb.get("improvements"):
                lines.extend(["", "### Improvements"])
                lines.extend([f"- {s}" for s in fb["improvements"]])

        if data.get("resume"):
            rs = data["resume"]
            lines.extend(
                [
                    "",
                    "## Resume ATS",
                    f"- File: {rs.get('filename')}",
                    f"- ATS score: {rs.get('ats_score') or '—'}",
                ]
            )
            if rs.get("suggestions"):
                lines.extend(["", "### Suggestions"])
                lines.extend([f"- {s}" for s in rs["suggestions"]])

        lines.append("")
        return "\n".join(lines)

    def _notify_ready(self, report: Report) -> None:
        self.db.add(
            Notification(
                user_id=report.user_id,
                title="Report ready",
                body=f"Your report “{report.title}” is ready to download.",
                channel=NotificationChannel.IN_APP,
                status=NotificationStatus.SENT,
                payload={"report_id": str(report.id), "type": _enum_val(report.report_type)},
                sent_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _default_title(report_type: ReportType) -> str:
        labels = {
            ReportType.WEEKLY_PROGRESS: "Weekly progress report",
            ReportType.MONTHLY_PROGRESS: "Monthly progress report",
            ReportType.INTERVIEW_SUMMARY: "Interview summary report",
            ReportType.RESUME_ATS: "Resume ATS report",
            ReportType.ROADMAP: "Prep roadmap report",
            ReportType.ADMIN_EXPORT: "Admin export",
        }
        return labels.get(report_type, "Progress report")
