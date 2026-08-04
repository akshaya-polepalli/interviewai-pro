"""
Interview answer evaluation.

Deterministic heuristics are the default (offline, testable).
Optional OpenAI enrichment when OPENAI_API_KEY is configured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.enums import InterviewType
from app.services.question_bank import COMPANY_FLAVOR

logger = get_logger(__name__)

STAR_MARKERS = {
    "situation": ("situation", "context", "background", "when i", "at my previous"),
    "task": ("task", "goal", "objective", "needed to", "responsible for"),
    "action": ("action", "i did", "i implemented", "i led", "i built", "we decided"),
    "result": ("result", "outcome", "impact", "increased", "reduced", "improved", "%"),
}

FILLERS = {"um", "uh", "like", "you know", "basically", "actually", "sort of", "kind of"}


@dataclass
class AnswerEval:
    score: Decimal
    coverage: Decimal
    communication: Decimal
    star_score: Decimal | None
    matched_points: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class InterviewEvalResult:
    overall_score: Decimal
    technical_score: Decimal
    communication_score: Decimal
    confidence_score: Decimal
    star_method_score: Decimal | None
    strengths: list[str]
    improvements: list[str]
    detailed_feedback: str
    per_answer: dict[str, AnswerEval]
    model_provider: str
    model_name: str | None
    raw_response: dict[str, Any] | None = None


class InterviewEvaluator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def evaluate_interview(
        self,
        *,
        interview_type: InterviewType | str,
        target_company: str | None,
        items: list[dict[str, Any]],
    ) -> InterviewEvalResult:
        """
        items: [{question_id, prompt, expected_points, answer_text, category}]
        """
        itype = interview_type.value if hasattr(interview_type, "value") else str(interview_type)
        per_answer: dict[str, AnswerEval] = {}
        tech_scores: list[Decimal] = []
        comm_scores: list[Decimal] = []
        star_scores: list[Decimal] = []

        for item in items:
            text = (item.get("answer_text") or "").strip()
            expected = item.get("expected_points") or []
            if isinstance(expected, str):
                expected = [expected]
            category = str(item.get("category") or "")
            ev = self._evaluate_answer(
                text=text,
                expected_points=list(expected),
                interview_type=itype,
                category=category,
            )
            qid = str(item["question_id"])
            per_answer[qid] = ev
            tech_scores.append(ev.coverage)
            comm_scores.append(ev.communication)
            if ev.star_score is not None:
                star_scores.append(ev.star_score)

        technical = _avg(tech_scores)
        communication = _avg(comm_scores)
        star = _avg(star_scores) if star_scores else None
        confidence = self._confidence_score(items)

        if itype in (
            InterviewType.BEHAVIORAL.value,
            InterviewType.HR.value,
            InterviewType.VOICE.value,
        ):
            overall = (
                (star or Decimal("50")) * Decimal("0.45")
                + communication * Decimal("0.30")
                + technical * Decimal("0.15")
                + confidence * Decimal("0.10")
            )
        else:
            overall = (
                technical * Decimal("0.55")
                + communication * Decimal("0.25")
                + confidence * Decimal("0.20")
            )

        overall = _clamp(overall)
        strengths, improvements = self._summarize(per_answer, itype)
        company_hint = COMPANY_FLAVOR.get(target_company or "general", COMPANY_FLAVOR["general"])
        detailed = (
            f"Overall score {overall:.0f}/100. "
            f"Content coverage {technical:.0f}, communication {communication:.0f}, "
            f"confidence {confidence:.0f}"
            + (f", STAR structure {star:.0f}" if star is not None else "")
            + f". {company_hint}"
        )

        result = InterviewEvalResult(
            overall_score=overall.quantize(Decimal("0.01")),
            technical_score=technical.quantize(Decimal("0.01")),
            communication_score=communication.quantize(Decimal("0.01")),
            confidence_score=confidence.quantize(Decimal("0.01")),
            star_method_score=star.quantize(Decimal("0.01")) if star is not None else None,
            strengths=strengths,
            improvements=improvements,
            detailed_feedback=detailed,
            per_answer=per_answer,
            model_provider="heuristic",
            model_name="interview-v1",
        )

        if self.settings.openai_api_key:
            enriched = self._openai_enrich(itype=itype, items=items, base=result)
            if enriched:
                return enriched
        return result

    def _evaluate_answer(
        self,
        *,
        text: str,
        expected_points: list[str],
        interview_type: str,
        category: str,
    ) -> AnswerEval:
        notes: list[str] = []
        if not text:
            return AnswerEval(
                score=Decimal("0"),
                coverage=Decimal("0"),
                communication=Decimal("0"),
                star_score=Decimal("0") if interview_type in ("behavioral", "hr", "voice") else None,
                notes=["Empty answer"],
            )

        words = re.findall(r"[a-zA-Z']+", text.lower())
        word_count = len(words)
        lower = text.lower()

        matched: list[str] = []
        missing: list[str] = []
        for point in expected_points:
            tokens = [t for t in re.findall(r"[a-zA-Z0-9/+-]+", point.lower()) if len(t) > 2]
            if not tokens:
                continue
            hits = sum(1 for t in tokens if t in lower)
            if hits >= max(1, len(tokens) // 2):
                matched.append(point)
            else:
                missing.append(point)

        if expected_points:
            coverage = Decimal(len(matched) / len(expected_points) * 100)
        else:
            # Length-based fallback
            if word_count < 30:
                coverage = Decimal("35")
            elif word_count < 80:
                coverage = Decimal("65")
            else:
                coverage = Decimal("80")
            notes.append("No expected points — used length heuristic")

        # Communication: sentence variety, fillers, length band
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        filler_hits = sum(lower.count(f) for f in FILLERS)
        filler_penalty = min(25, filler_hits * 4)
        length_score = 40
        if 40 <= word_count <= 250:
            length_score = 85
        elif 25 <= word_count < 40 or 250 < word_count <= 400:
            length_score = 70
        elif word_count > 400:
            length_score = 60
            notes.append("Answer is quite long — tighten for interviews")
        else:
            notes.append("Answer is short — add concrete detail")
        structure_bonus = 10 if len(sentences) >= 2 else 0
        communication = _clamp(Decimal(length_score + structure_bonus - filler_penalty))

        star_score = None
        if interview_type in ("behavioral", "hr", "voice") or category in ("behavioral", "hr"):
            dims_hit = 0
            for markers in STAR_MARKERS.values():
                if any(m in lower for m in markers):
                    dims_hit += 1
            star_score = Decimal(dims_hit / 4 * 100)
            if dims_hit < 3:
                notes.append("Strengthen STAR structure (Situation → Task → Action → Result)")

        # Blend into per-answer score
        if star_score is not None:
            score = star_score * Decimal("0.5") + coverage * Decimal("0.3") + communication * Decimal("0.2")
        else:
            score = coverage * Decimal("0.7") + communication * Decimal("0.3")

        return AnswerEval(
            score=_clamp(score).quantize(Decimal("0.01")),
            coverage=_clamp(coverage).quantize(Decimal("0.01")),
            communication=communication.quantize(Decimal("0.01")),
            star_score=star_score.quantize(Decimal("0.01")) if star_score is not None else None,
            matched_points=matched,
            missing_points=missing,
            notes=notes,
        )

    def _confidence_score(self, items: list[dict[str, Any]]) -> Decimal:
        answered = [i for i in items if (i.get("answer_text") or "").strip()]
        if not items:
            return Decimal("0")
        completion = Decimal(len(answered) / len(items) * 100)
        # Prefer answers with numbers / concrete outcomes
        concrete = 0
        for i in answered:
            text = i.get("answer_text") or ""
            if re.search(r"\d", text) or any(
                w in text.lower() for w in ("result", "impact", "because", "for example")
            ):
                concrete += 1
        concreteness = Decimal(concrete / max(len(answered), 1) * 100)
        return _clamp((completion * Decimal("0.6") + concreteness * Decimal("0.4")))

    def _summarize(
        self, per_answer: dict[str, AnswerEval], interview_type: str
    ) -> tuple[list[str], list[str]]:
        strengths: list[str] = []
        improvements: list[str] = []
        if not per_answer:
            return ["No answers submitted"], ["Answer every question before completing"]

        avg_comm = _avg([e.communication for e in per_answer.values()])
        avg_cov = _avg([e.coverage for e in per_answer.values()])
        if avg_cov >= 70:
            strengths.append("Strong coverage of expected technical / topic points")
        if avg_comm >= 70:
            strengths.append("Clear, well-structured communication")
        if interview_type in ("behavioral", "hr", "voice"):
            stars = [e.star_score for e in per_answer.values() if e.star_score is not None]
            if stars and _avg(stars) >= 70:
                strengths.append("Good use of STAR storytelling")
            elif stars:
                improvements.append("Use STAR more consistently across spoken answers")

        missing_pool: list[str] = []
        for e in per_answer.values():
            missing_pool.extend(e.missing_points)
            improvements.extend(e.notes)
        for point in missing_pool[:3]:
            improvements.append(f"Mention: {point}")

        if avg_cov < 60:
            improvements.append("Anchor answers to concrete concepts and tradeoffs")
        if avg_comm < 60:
            improvements.append("Aim for 60–180 words with a clear beginning and end")

        # Dedupe preserve order
        strengths = list(dict.fromkeys(strengths)) or ["Completed the interview — keep practicing"]
        improvements = list(dict.fromkeys(improvements))[:6]
        return strengths, improvements

    def _openai_enrich(
        self,
        *,
        itype: str,
        items: list[dict[str, Any]],
        base: InterviewEvalResult,
    ) -> InterviewEvalResult | None:
        transcript = []
        for i, item in enumerate(items, start=1):
            transcript.append(
                f"Q{i}: {item.get('prompt')}\nA{i}: {item.get('answer_text') or '(empty)'}"
            )
        prompt = (
            f"You are an interview coach. Interview type: {itype}.\n"
            f"Heuristic scores — overall {base.overall_score}, technical {base.technical_score}, "
            f"communication {base.communication_score}.\n"
            "Write 2 strengths and 3 improvements as short bullets, then a 3-sentence coaching summary.\n\n"
            + "\n\n".join(transcript)
        )
        try:
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json={
                        "model": self.settings.openai_model,
                        "messages": [
                            {"role": "system", "content": "Be concise and actionable."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                base.detailed_feedback = content
                base.model_provider = "openai"
                base.model_name = self.settings.openai_model
                base.raw_response = {"provider": "openai", "preview": content[:500]}
                return base
        except Exception:
            logger.exception("interview_openai_enrich_failed")
            return None


def _avg(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _clamp(value: Decimal, low: Decimal = Decimal("0"), high: Decimal = Decimal("100")) -> Decimal:
    return max(low, min(high, value))
