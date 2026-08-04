"""Unit tests for company track catalog."""

from app.services.company_tracks import get_track, list_tracks


def test_catalog_covers_major_targets() -> None:
    companies = {t.company for t in list_tracks()}
    assert {"google", "amazon", "microsoft", "meta", "openai", "general"} <= companies


def test_google_milestones_have_weeks_and_links() -> None:
    track = get_track("google")
    assert track is not None
    assert track.weeks >= 3
    assert all(m.week >= 1 for m in track.milestones)
    assert any(m.resource_path for m in track.milestones)
    assert any(m.auto_rule for m in track.milestones)


def test_get_track_case_insensitive() -> None:
    assert get_track("Amazon") is not None
    assert get_track("nope") is None
