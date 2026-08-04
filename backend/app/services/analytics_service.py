"""
Progress analytics recompute + achievement unlocks.

Rollup strategy: recompute from source tables on demand / after key events.
Good enough for SaaS MVP; later swap to incremental counters + nightly job.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.models import (
    Achievement,
    Analytics,
    Interview,
    Question,
    Resume,
    ResumeAnalysis,
    Submission,
    UserAchievement,
)
from app.models.enums import InterviewStatus, InterviewType, SubmissionStatus
from app.schemas.analytics import (
    AchievementItem,
    AnalyticsBundleResponse,
    AnalyticsResponse,
    RoadmapItem,
    SeriesPoint,
    SkillRadar,
)

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create(self, user_id: UUID) -> Analytics:
        row = self.db.scalar(select(Analytics).where(Analytics.user_id == user_id))
        if row:
            return row
        row = Analytics(user_id=user_id)
        self.db.add(row)
        self.db.flush()
        return row

    def get_bundle(self, user_id: UUID, *, refresh: bool = False) -> AnalyticsBundleResponse:
        recently: list[str] = []
        if refresh:
            recently = self.recompute(user_id)
        else:
            self.get_or_create(user_id)
        analytics = self.get_or_create(user_id)
        latest_ats = self._latest_ats(user_id)
        return AnalyticsBundleResponse(
            analytics=self._to_response(analytics, latest_ats=latest_ats),
            achievements=self.list_achievements(user_id),
            recently_unlocked=recently,
        )

    def recompute(self, user_id: UUID) -> list[str]:
        analytics = self.get_or_create(user_id)

        interviews = list(
            self.db.scalars(
                select(Interview)
                .options(
                    selectinload(Interview.feedback),
                    selectinload(Interview.questions).selectinload(Question.answers),
                )
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

        completed = [
            i
            for i in interviews
            if _status(i.status)
            in {InterviewStatus.COMPLETED.value, InterviewStatus.EVALUATED.value}
        ]
        scores = [
            float(i.overall_score)
            for i in completed
            if i.overall_score is not None
        ]

        analytics.total_interviews = len(interviews)
        analytics.completed_interviews = len(completed)
        analytics.average_score = (
            Decimal(str(round(sum(scores) / len(scores), 2))) if scores else None
        )
        analytics.coding_submissions = len(submissions)
        analytics.coding_accepted = sum(
            1 for s in submissions if _status(s.status) == SubmissionStatus.ACCEPTED.value
        )

        activity_days = self._activity_days(interviews, submissions, resumes)
        current, longest = self._streaks(activity_days)
        analytics.current_streak_days = current
        analytics.longest_streak_days = max(longest, analytics.longest_streak_days or 0)

        strong, weak = self._topics(interviews)
        analytics.strong_topics = strong
        analytics.weak_topics = weak
        analytics.skill_radar = self._skill_radar(completed, submissions, resumes).model_dump()
        analytics.weekly_series = [
            p.model_dump() for p in self._weekly_series(interviews, submissions, resumes)
        ]
        analytics.roadmap = [r.model_dump() for r in self._roadmap(completed, submissions, resumes)]

        self.db.add(analytics)
        self.db.flush()
        unlocked = self._unlock_achievements(user_id, analytics, resumes)
        self.db.commit()
        return unlocked

    def list_achievements(self, user_id: UUID) -> list[AchievementItem]:
        catalog = list(self.db.scalars(select(Achievement).order_by(Achievement.points)).all())
        unlocked_rows = list(
            self.db.scalars(
                select(UserAchievement)
                .options(selectinload(UserAchievement.achievement))
                .where(UserAchievement.user_id == user_id)
            ).all()
        )
        by_code = {
            ua.achievement.code: ua.unlocked_at
            for ua in unlocked_rows
            if ua.achievement is not None
        }
        return [
            AchievementItem(
                code=a.code,
                title=a.title,
                description=a.description,
                points=a.points,
                unlocked=a.code in by_code,
                unlocked_at=by_code.get(a.code),
            )
            for a in catalog
        ]

    def _to_response(self, row: Analytics, *, latest_ats: Decimal | None) -> AnalyticsResponse:
        return AnalyticsResponse(
            user_id=row.user_id,
            total_interviews=row.total_interviews,
            completed_interviews=row.completed_interviews,
            average_score=row.average_score,
            coding_submissions=row.coding_submissions,
            coding_accepted=row.coding_accepted,
            current_streak_days=row.current_streak_days,
            longest_streak_days=row.longest_streak_days,
            strong_topics=row.strong_topics,
            weak_topics=row.weak_topics,
            skill_radar=row.skill_radar,
            weekly_series=row.weekly_series,
            roadmap=row.roadmap,
            latest_ats_score=latest_ats,
            updated_at=row.updated_at,
        )

    def _latest_ats(self, user_id: UUID) -> Decimal | None:
        score = self.db.scalar(
            select(ResumeAnalysis.ats_score)
            .join(Resume, Resume.id == ResumeAnalysis.resume_id)
            .where(Resume.user_id == user_id, Resume.is_deleted.is_(False))
            .order_by(ResumeAnalysis.updated_at.desc())
            .limit(1)
        )
        return score

    def _activity_days(
        self,
        interviews: list[Interview],
        submissions: list[Submission],
        resumes: list[Resume],
    ) -> set[date]:
        days: set[date] = set()
        for i in interviews:
            if i.completed_at:
                days.add(i.completed_at.astimezone(UTC).date())
            elif i.created_at:
                days.add(i.created_at.astimezone(UTC).date())
        for s in submissions:
            if s.created_at:
                days.add(s.created_at.astimezone(UTC).date())
        for r in resumes:
            if r.created_at:
                days.add(r.created_at.astimezone(UTC).date())
        return days

    def _streaks(self, days: set[date]) -> tuple[int, int]:
        if not days:
            return 0, 0
        ordered = sorted(days)
        longest = 1
        run = 1
        for prev, cur in zip(ordered, ordered[1:]):
            if (cur - prev).days == 1:
                run += 1
                longest = max(longest, run)
            else:
                run = 1

        today = datetime.now(UTC).date()
        current = 0
        cursor = today
        # Allow yesterday to start streak if no activity today yet
        if cursor not in days:
            cursor = today - timedelta(days=1)
        while cursor in days:
            current += 1
            cursor -= timedelta(days=1)
        return current, longest

    def _topics(self, interviews: list[Interview]) -> tuple[list[str], list[str]]:
        category_scores: dict[str, list[float]] = {}
        for interview in interviews:
            for q in interview.questions or []:
                cat = _status(q.category) if q.category else "other"
                for ans in q.answers or []:
                    if ans.score is not None:
                        category_scores.setdefault(cat, []).append(float(ans.score))
        averages = {
            cat: sum(vals) / len(vals) for cat, vals in category_scores.items() if vals
        }
        if not averages:
            return [], []
        ranked = sorted(averages.items(), key=lambda x: x[1], reverse=True)
        strong = [c.replace("_", " ") for c, s in ranked[:3] if s >= 60]
        weak = [c.replace("_", " ") for c, s in ranked[-3:] if s < 60]
        return strong, weak

    def _skill_radar(
        self,
        completed: list[Interview],
        submissions: list[Submission],
        resumes: list[Resume],
    ) -> SkillRadar:
        tech_scores: list[float] = []
        beh_scores: list[float] = []
        comm_scores: list[float] = []
        for i in completed:
            fb = i.feedback
            itype = _status(i.interview_type)
            if fb and fb.technical_score is not None and itype == InterviewType.TECHNICAL.value:
                tech_scores.append(float(fb.technical_score))
            if fb and fb.star_method_score is not None and itype in {
                InterviewType.BEHAVIORAL.value,
                InterviewType.HR.value,
            }:
                beh_scores.append(float(fb.star_method_score))
            if fb and fb.communication_score is not None:
                comm_scores.append(float(fb.communication_score))
            if i.overall_score is not None and itype == InterviewType.TECHNICAL.value:
                tech_scores.append(float(i.overall_score))

        coding = 0.0
        if submissions:
            coding = (
                sum(
                    1
                    for s in submissions
                    if _status(s.status) == SubmissionStatus.ACCEPTED.value
                )
                / len(submissions)
            ) * 100

        resume_scores = [
            float(r.analysis.ats_score)
            for r in resumes
            if r.analysis and r.analysis.ats_score is not None
        ]

        return SkillRadar(
            technical=_avg(tech_scores),
            behavioral=_avg(beh_scores),
            communication=_avg(comm_scores),
            coding=round(coding, 1),
            resume=_avg(resume_scores),
        )

    def _weekly_series(
        self,
        interviews: list[Interview],
        submissions: list[Submission],
        resumes: list[Resume],
    ) -> list[SeriesPoint]:
        today = datetime.now(UTC).date()
        # Monday-based weeks, last 8
        points: list[SeriesPoint] = []
        for weeks_ago in range(7, -1, -1):
            start = today - timedelta(days=today.weekday() + weeks_ago * 7)
            end = start + timedelta(days=6)
            label = start.strftime("%b %d")
            iv = sum(
                1
                for i in interviews
                if i.created_at and start <= i.created_at.astimezone(UTC).date() <= end
            )
            code = sum(
                1
                for s in submissions
                if s.created_at and start <= s.created_at.astimezone(UTC).date() <= end
            )
            res = sum(
                1
                for r in resumes
                if r.created_at and start <= r.created_at.astimezone(UTC).date() <= end
            )
            points.append(SeriesPoint(label=label, interviews=iv, coding=code, resumes=res))
        return points

    def _roadmap(
        self,
        completed: list[Interview],
        submissions: list[Submission],
        resumes: list[Resume],
    ) -> list[RoadmapItem]:
        has_resume = len(resumes) > 0
        ats_ok = any(
            r.analysis and r.analysis.ats_score is not None and float(r.analysis.ats_score) >= 70
            for r in resumes
        )
        has_interview = len(completed) > 0
        has_accepted = any(
            _status(s.status) == SubmissionStatus.ACCEPTED.value for s in submissions
        )
        high_interview = any(
            i.overall_score is not None and float(i.overall_score) >= 75 for i in completed
        )
        return [
            RoadmapItem(
                id="upload_resume",
                title="Upload a resume",
                done=has_resume,
                hint="Go to Resumes and upload PDF/DOCX/TXT",
            ),
            RoadmapItem(
                id="ats_70",
                title="Reach ATS score 70+",
                done=ats_ok,
                hint="Re-analyze with a target role and job description",
            ),
            RoadmapItem(
                id="first_interview",
                title="Complete a mock interview",
                done=has_interview,
                hint="Try a technical or behavioral round",
            ),
            RoadmapItem(
                id="first_accepted",
                title="Get an accepted coding submission",
                done=has_accepted,
                hint="Start with Two Sum on the Coding page",
            ),
            RoadmapItem(
                id="interview_75",
                title="Score 75+ on an interview",
                done=high_interview,
                hint="Use STAR for behavioral; cover expected points for technical",
            ),
        ]

    def _unlock_achievements(
        self, user_id: UUID, analytics: Analytics, resumes: list[Resume]
    ) -> list[str]:
        catalog = {
            a.code: a for a in self.db.scalars(select(Achievement)).all()
        }
        already = {
            ua.achievement_id
            for ua in self.db.scalars(
                select(UserAchievement).where(UserAchievement.user_id == user_id)
            ).all()
        }
        unlocked_codes: list[str] = []

        def unlock(code: str) -> None:
            ach = catalog.get(code)
            if ach is None or ach.id in already:
                return
            self.db.add(
                UserAchievement(
                    user_id=user_id,
                    achievement_id=ach.id,
                    unlocked_at=datetime.now(UTC),
                )
            )
            already.add(ach.id)
            unlocked_codes.append(code)

        if analytics.completed_interviews >= 1:
            unlock("first_interview")
        if analytics.coding_accepted >= 1:
            unlock("first_accepted")
        if analytics.current_streak_days >= 7 or analytics.longest_streak_days >= 7:
            unlock("week_streak_7")
        if any(
            r.analysis and r.analysis.ats_score is not None and float(r.analysis.ats_score) >= 80
            for r in resumes
        ):
            unlock("ats_80")
        # first_login is typically granted at login; grant if any activity exists
        if (
            analytics.total_interviews
            or analytics.coding_submissions
            or resumes
        ):
            unlock("first_login")

        self.db.flush()
        return unlocked_codes


def touch_analytics(db: Session, user_id: UUID) -> None:
    """Best-effort rollup update — never breaks the primary user action."""
    try:
        AnalyticsService(db).recompute(user_id)
    except Exception:
        logger.exception("analytics_recompute_failed", user_id=str(user_id))


def _status(value: object | None) -> str:
    if value is None:
        return ""
    return value.value if hasattr(value, "value") else str(value)


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)
