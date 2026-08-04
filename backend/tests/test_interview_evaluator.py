"""Unit tests for interview evaluator heuristics."""

from __future__ import annotations

from app.services.interview_evaluator import InterviewEvaluator


def test_evaluator_rewards_expected_points() -> None:
    ev = InterviewEvaluator()
    result = ev.evaluate_interview(
        interview_type="technical",
        target_company="general",
        items=[
            {
                "question_id": "q1",
                "prompt": "Rate limiter?",
                "expected_points": ["token bucket", "Redis", "burst handling"],
                "answer_text": (
                    "I would implement a token bucket in Redis for per-user limits, "
                    "allowing short burst handling while enforcing a sustained rate. "
                    "For example this cut abuse by 30%."
                ),
                "category": "system_design",
            }
        ],
    )
    assert float(result.overall_score) > 40
    assert result.per_answer["q1"].matched_points


def test_evaluator_star_for_behavioral() -> None:
    ev = InterviewEvaluator()
    result = ev.evaluate_interview(
        interview_type="behavioral",
        target_company="amazon",
        items=[
            {
                "question_id": "q1",
                "prompt": "Conflict?",
                "expected_points": ["Situation", "Action", "Result"],
                "answer_text": (
                    "Situation: We disagreed on API design. Task: Align the team. "
                    "Action: I facilitated a spike and we decided on versioning. "
                    "Result: We shipped on time and reduced support tickets."
                ),
                "category": "behavioral",
            }
        ],
    )
    assert result.star_method_score is not None
    assert float(result.star_method_score) >= 75
