"""
Company-specific prep roadmaps.

Catalog is static (company_tracks.py). Progress = auto signals from activity
OR manual milestone checks on the enrollment row.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import (
    Interview,
    Question,
    Report,
    Resume,
    StudyPlan,
    Submission,
    UserCompanyRoadmap,
)
from app.models.enums import (
    InterviewStatus,
    InterviewType,
    ReportStatus,
    RoadmapEnrollmentStatus,
    StudyPlanStatus,
    SubmissionStatus,
    TargetCompany,
)
from app.schemas.roadmaps import (
    CompanyTrackDetail,
    CompanyTrackSummary,
    EnrollRoadmapRequest,
    MilestoneResponse,
)
from app.services.company_tracks import CompanyTrackDef, get_track, list_tracks


def _enum_val(value: object | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


class RoadmapService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self, user_id: UUID) -> list[CompanyTrackSummary]:
        enrollments = {
            _enum_val(e.company): e
            for e in self.db.scalars(
                select(UserCompanyRoadmap).where(UserCompanyRoadmap.user_id == user_id)
            ).all()
        }
        signals = self._signals(user_id)
        out: list[CompanyTrackSummary] = []
        for track in list_tracks():
            enr = enrollments.get(track.company)
            milestones = self._milestone_states(track, enr, signals)
            done = sum(1 for m in milestones if m.done)
            total = len(milestones) or 1
            out.append(
                CompanyTrackSummary(
                    company=track.company,
                    name=track.name,
                    tagline=track.tagline,
                    weeks=track.weeks,
                    focus=list(track.focus),
                    milestone_count=len(track.milestones),
                    enrolled=enr is not None
                    and _enum_val(enr.status) != RoadmapEnrollmentStatus.ARCHIVED.value,
                    progress_pct=int(round(100 * done / total)),
                    status=_enum_val(enr.status) if enr else None,
                )
            )
        return out

    def get_track(self, user_id: UUID, company: str) -> CompanyTrackDetail:
        track = get_track(company)
        if track is None:
            raise NotFoundError("Company track not found")
        enrollment = self._enrollment(user_id, track.company)
        signals = self._signals(user_id)
        return self._detail(track, enrollment, signals)

    def enroll(self, user_id: UUID, payload: EnrollRoadmapRequest) -> CompanyTrackDetail:
        company = payload.company.value if isinstance(payload.company, TargetCompany) else str(payload.company)
        track = get_track(company)
        if track is None:
            raise NotFoundError("Company track not found")

        existing = self._enrollment(user_id, track.company)
        if existing and _enum_val(existing.status) != RoadmapEnrollmentStatus.ARCHIVED.value:
            raise ConflictError("Already enrolled in this company track")

        if existing:
            existing.status = RoadmapEnrollmentStatus.ACTIVE
            existing.notes = payload.notes
            existing.manual_done = existing.manual_done or []
            self.db.add(existing)
        else:
            existing = UserCompanyRoadmap(
                user_id=user_id,
                company=TargetCompany(track.company),
                status=RoadmapEnrollmentStatus.ACTIVE,
                manual_done=[],
                notes=payload.notes,
            )
            self.db.add(existing)

        # Soft-archive other active enrollments so one primary track is clear in UI.
        others = list(
            self.db.scalars(
                select(UserCompanyRoadmap).where(
                    UserCompanyRoadmap.user_id == user_id,
                    UserCompanyRoadmap.company != TargetCompany(track.company),
                    UserCompanyRoadmap.status == RoadmapEnrollmentStatus.ACTIVE,
                )
            ).all()
        )
        for row in others:
            row.status = RoadmapEnrollmentStatus.ARCHIVED
            self.db.add(row)

        self.db.commit()
        return self.get_track(user_id, track.company)

    def toggle_milestone(
        self, user_id: UUID, company: str, milestone_id: str, *, is_done: bool
    ) -> CompanyTrackDetail:
        track = get_track(company)
        if track is None:
            raise NotFoundError("Company track not found")
        enrollment = self._enrollment(user_id, track.company)
        if enrollment is None or _enum_val(enrollment.status) == RoadmapEnrollmentStatus.ARCHIVED.value:
            raise ValidationAppError("Enroll in this track before checking milestones")

        ids = {m.id for m in track.milestones}
        if milestone_id not in ids:
            raise ValidationAppError("Unknown milestone for this track")

        manual = list(enrollment.manual_done or [])
        if is_done and milestone_id not in manual:
            manual.append(milestone_id)
        if not is_done and milestone_id in manual:
            manual = [m for m in manual if m != milestone_id]
        enrollment.manual_done = manual

        signals = self._signals(user_id)
        states = self._milestone_states(track, enrollment, signals)
        if states and all(m.done for m in states):
            enrollment.status = RoadmapEnrollmentStatus.COMPLETED
        elif _enum_val(enrollment.status) == RoadmapEnrollmentStatus.COMPLETED.value:
            enrollment.status = RoadmapEnrollmentStatus.ACTIVE

        self.db.add(enrollment)
        self.db.commit()
        return self.get_track(user_id, track.company)

    def archive(self, user_id: UUID, company: str) -> CompanyTrackDetail:
        track = get_track(company)
        if track is None:
            raise NotFoundError("Company track not found")
        enrollment = self._enrollment(user_id, track.company)
        if enrollment is None:
            raise NotFoundError("Enrollment not found")
        enrollment.status = RoadmapEnrollmentStatus.ARCHIVED
        self.db.add(enrollment)
        self.db.commit()
        return self.get_track(user_id, track.company)

    # ----- internals -----

    def _enrollment(self, user_id: UUID, company: str) -> UserCompanyRoadmap | None:
        return self.db.scalar(
            select(UserCompanyRoadmap).where(
                UserCompanyRoadmap.user_id == user_id,
                UserCompanyRoadmap.company == TargetCompany(company),
            )
        )

    def _signals(self, user_id: UUID) -> dict[str, bool]:
        interviews = list(
            self.db.scalars(
                select(Interview)
                .options(selectinload(Interview.questions).selectinload(Question.answers))
                .where(Interview.user_id == user_id)
            ).all()
        )
        submissions = list(
            self.db.scalars(select(Submission).where(Submission.user_id == user_id)).all()
        )
        resumes = list(
            self.db.scalars(
                select(Resume)
                .options(selectinload(Resume.analysis))
                .where(Resume.user_id == user_id, Resume.is_deleted.is_(False))
            ).all()
        )
        plans = list(
            self.db.scalars(select(StudyPlan).where(StudyPlan.user_id == user_id)).all()
        )
        reports = list(
            self.db.scalars(select(Report).where(Report.user_id == user_id)).all()
        )

        finished = {
            InterviewStatus.COMPLETED.value,
            InterviewStatus.EVALUATED.value,
        }
        completed = [i for i in interviews if _enum_val(i.status) in finished]

        return {
            "ats_70": any(
                r.analysis and r.analysis.ats_score is not None and float(r.analysis.ats_score) >= 70
                for r in resumes
            ),
            "coding_accepted": any(
                _enum_val(s.status) == SubmissionStatus.ACCEPTED.value for s in submissions
            ),
            "interview_done": len(completed) > 0,
            "behavioral_done": any(
                _enum_val(i.interview_type) == InterviewType.BEHAVIORAL.value for i in completed
            ),
            "voice_done": any(
                _enum_val(i.interview_type) == InterviewType.VOICE.value for i in completed
            )
            or any(
                _enum_val(i.interview_type) == InterviewType.VOICE.value
                and any(q.answers for q in (i.questions or []))
                for i in interviews
            ),
            "interview_75": any(
                i.overall_score is not None and float(i.overall_score) >= 75 for i in completed
            ),
            "study_plan": any(
                _enum_val(p.status) in {
                    StudyPlanStatus.ACTIVE.value,
                    StudyPlanStatus.COMPLETED.value,
                }
                for p in plans
            ),
            "report_ready": any(
                _enum_val(r.status) == ReportStatus.READY.value for r in reports
            ),
        }

    def _milestone_states(
        self,
        track: CompanyTrackDef,
        enrollment: UserCompanyRoadmap | None,
        signals: dict[str, bool],
    ) -> list[MilestoneResponse]:
        manual = set(enrollment.manual_done or []) if enrollment else set()
        out: list[MilestoneResponse] = []
        for m in track.milestones:
            via: str | None = None
            done = False
            if m.auto_rule and signals.get(m.auto_rule):
                done = True
                via = "auto"
            elif m.id in manual:
                done = True
                via = "manual"
            out.append(
                MilestoneResponse(
                    id=m.id,
                    title=m.title,
                    description=m.description,
                    week=m.week,
                    category=m.category,
                    resource_path=m.resource_path,
                    auto_rule=m.auto_rule,
                    done=done,
                    done_via=via,
                )
            )
        return out

    def _detail(
        self,
        track: CompanyTrackDef,
        enrollment: UserCompanyRoadmap | None,
        signals: dict[str, bool],
    ) -> CompanyTrackDetail:
        milestones = self._milestone_states(track, enrollment, signals)
        done = sum(1 for m in milestones if m.done)
        total = len(milestones) or 1
        enrolled = (
            enrollment is not None
            and _enum_val(enrollment.status) != RoadmapEnrollmentStatus.ARCHIVED.value
        )
        return CompanyTrackDetail(
            company=track.company,
            name=track.name,
            tagline=track.tagline,
            weeks=track.weeks,
            focus=list(track.focus),
            interview_loop=list(track.interview_loop),
            principles=list(track.principles),
            milestones=milestones,
            enrolled=enrolled,
            enrollment_id=enrollment.id if enrollment and enrolled else None,
            status=_enum_val(enrollment.status) if enrollment else None,
            notes=enrollment.notes if enrollment else None,
            done_count=done,
            milestone_count=len(milestones),
            progress_pct=int(round(100 * done / total)),
            created_at=enrollment.created_at if enrollment else None,
            updated_at=enrollment.updated_at if enrollment else None,
        )
