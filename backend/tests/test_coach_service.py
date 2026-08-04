"""
Unit tests for coach plan focus derivation (no Postgres).
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.analytics import AnalyticsResponse, SkillRadar
from app.services.coach_service import CoachService


def _analytics(**kwargs) -> AnalyticsResponse:
    base = dict(
        user_id=uuid4(),
        total_interviews=0,
        completed_interviews=0,
        average_score=None,
        coding_submissions=0,
        coding_accepted=0,
        current_streak_days=0,
        longest_streak_days=0,
        strong_topics=[],
        weak_topics=[],
        skill_radar=SkillRadar(
            technical=40, behavioral=70, communication=65, coding=30, resume=50
        ),
        weekly_series=[],
        roadmap=[],
        latest_ats_score=None,
        updated_at=datetime.now(UTC),
    )
    base.update(kwargs)
    return AnalyticsResponse(**base)


def test_normalize_focus_aliases() -> None:
    assert CoachService._normalize_focus("System Design") == "system_design"
    assert CoachService._normalize_focus("DSA") == "algorithms"
    assert CoachService._normalize_focus("ATS keywords") == "resume"


def test_derive_focus_prefers_low_radar_and_weak_topics() -> None:
    svc = CoachService.__new__(CoachService)
    a = _analytics(weak_topics=["algorithms"], coding_submissions=1, coding_accepted=0)
    focus = svc._derive_focus(a, override=None)
    assert "coding" in focus or "algorithms" in focus
    assert "general" in focus


def test_derive_focus_respects_override() -> None:
    svc = CoachService.__new__(CoachService)
    a = _analytics()
    focus = svc._derive_focus(a, override=["Behavioral", "Resume"])
    assert focus[0] == "behavioral"
    assert "resume" in focus
