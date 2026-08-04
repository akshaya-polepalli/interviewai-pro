"""
ATS scoring engine.

Primary path is deterministic heuristics (fast, free, testable).
Optional LLM suggestions enrich the response when an API key is configured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.models.enums import TargetRole
from app.services.resume_parser import ParsedResume

logger = get_logger(__name__)

ROLE_KEYWORDS: dict[str, list[str]] = {
    TargetRole.SOFTWARE_ENGINEER.value: [
        "python", "java", "javascript", "typescript", "react", "node", "sql",
        "git", "api", "rest", "docker", "kubernetes", "aws", "ci/cd", "testing",
        "algorithms", "data structures", "system design", "microservices",
    ],
    TargetRole.BACKEND_ENGINEER.value: [
        "python", "java", "go", "fastapi", "django", "spring", "postgresql",
        "mysql", "redis", "kafka", "rabbitmq", "docker", "kubernetes", "aws",
        "rest", "graphql", "grpc", "sqlalchemy", "celery", "observability",
    ],
    TargetRole.FRONTEND_ENGINEER.value: [
        "javascript", "typescript", "react", "next.js", "vue", "css", "html",
        "tailwind", "redux", "webpack", "vite", "accessibility", "responsive",
        "jest", "cypress", "performance",
    ],
    TargetRole.FULL_STACK_ENGINEER.value: [
        "javascript", "typescript", "react", "node", "python", "sql", "api",
        "docker", "aws", "postgresql", "mongodb", "rest", "ci/cd", "testing",
    ],
    TargetRole.DATA_ANALYST.value: [
        "sql", "python", "excel", "tableau", "power bi", "pandas", "statistics",
        "etl", "dashboard", "visualization", "a/b testing", "looker",
    ],
    TargetRole.ML_ENGINEER.value: [
        "python", "machine learning", "deep learning", "pytorch", "tensorflow",
        "scikit-learn", "nlp", "computer vision", "mlops", "feature engineering",
        "model serving", "docker", "aws", "data pipelines",
    ],
    TargetRole.DEVOPS_ENGINEER.value: [
        "docker", "kubernetes", "terraform", "ansible", "ci/cd", "aws", "gcp",
        "azure", "linux", "monitoring", "prometheus", "grafana", "jenkins",
        "github actions", "networking",
    ],
    TargetRole.STUDENT.value: [
        "internship", "project", "python", "java", "javascript", "git", "sql",
        "data structures", "algorithms", "coursework",
    ],
    TargetRole.OTHER.value: [
        "communication", "leadership", "collaboration", "problem solving",
        "project management", "analytics",
    ],
}

ACTION_VERBS = {
    "built", "designed", "developed", "led", "implemented", "optimized",
    "improved", "created", "launched", "delivered", "automated", "reduced",
    "increased", "migrated", "architected", "shipped", "scaled",
}


@dataclass
class ATSResult:
    ats_score: Decimal
    keyword_match_score: Decimal
    matched_keywords: list[str] = field(default_factory=list)
    missing_keywords: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    section_scores: dict[str, float] = field(default_factory=dict)
    model_provider: str | None = None
    model_name: str | None = None
    raw_response: dict | None = None


class ATSAnalyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def analyze(
        self,
        parsed: ParsedResume,
        *,
        target_role: str | None = None,
        job_description: str | None = None,
    ) -> ATSResult:
        role_key = target_role or TargetRole.SOFTWARE_ENGINEER.value
        keywords = list(ROLE_KEYWORDS.get(role_key, ROLE_KEYWORDS[TargetRole.OTHER.value]))
        if job_description:
            extra = self._extract_jd_keywords(job_description)
            keywords = list(dict.fromkeys(keywords + extra))

        text_lower = parsed.raw_text.lower()
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        missing = [kw for kw in keywords if kw.lower() not in text_lower]
        keyword_score = (len(matched) / len(keywords) * 100.0) if keywords else 0.0

        section_scores = {
            "contact": self._score_contact(parsed),
            "summary": 100.0 if parsed.sections.get("summary") else 35.0,
            "experience": 100.0 if parsed.sections.get("experience") else 25.0,
            "education": 100.0 if parsed.sections.get("education") else 40.0,
            "skills": 100.0 if parsed.sections.get("skills") else 30.0,
            "length": self._score_length(parsed.word_count),
            "action_verbs": self._score_action_verbs(text_lower),
            "keywords": round(keyword_score, 2),
        }

        # Weighted overall score
        weights = {
            "contact": 0.10,
            "summary": 0.10,
            "experience": 0.25,
            "education": 0.10,
            "skills": 0.15,
            "length": 0.05,
            "action_verbs": 0.10,
            "keywords": 0.15,
        }
        overall = sum(section_scores[k] * weights[k] for k in weights)

        suggestions = self._heuristic_suggestions(parsed, matched, missing, section_scores)
        provider = "heuristic"
        model_name = "ats-v1"
        raw: dict | None = {"engine": "heuristic", "weights": weights}

        if self.settings.ats_use_llm_suggestions and self.settings.openai_api_key:
            llm_suggestions = self._llm_suggestions(parsed.raw_text[:6000], role_key, missing[:12])
            if llm_suggestions:
                suggestions = list(dict.fromkeys(suggestions + llm_suggestions))[:12]
                provider = "openai+heuristic"
                model_name = self.settings.openai_model
                raw = {"engine": "hybrid", "llm_count": len(llm_suggestions)}

        return ATSResult(
            ats_score=Decimal(str(round(overall, 2))),
            keyword_match_score=Decimal(str(round(keyword_score, 2))),
            matched_keywords=matched,
            missing_keywords=missing[:25],
            suggestions=suggestions[:12],
            section_scores=section_scores,
            model_provider=provider,
            model_name=model_name,
            raw_response=raw,
        )

    def _score_contact(self, parsed: ParsedResume) -> float:
        score = 0.0
        if parsed.email:
            score += 50
        if parsed.phone:
            score += 30
        if parsed.links:
            score += 20
        return min(score, 100.0)

    def _score_length(self, word_count: int) -> float:
        if 350 <= word_count <= 900:
            return 100.0
        if 250 <= word_count < 350 or 900 < word_count <= 1200:
            return 75.0
        if word_count < 200:
            return 40.0
        return 55.0

    def _score_action_verbs(self, text_lower: str) -> float:
        hits = sum(1 for verb in ACTION_VERBS if re.search(rf"\b{re.escape(verb)}\b", text_lower))
        return min(hits / 8 * 100.0, 100.0)

    def _heuristic_suggestions(
        self,
        parsed: ParsedResume,
        matched: list[str],
        missing: list[str],
        section_scores: dict[str, float],
    ) -> list[str]:
        tips: list[str] = []
        if section_scores["contact"] < 80:
            tips.append("Add a professional email, phone number, and LinkedIn/GitHub link near the top.")
        if section_scores["summary"] < 80:
            tips.append("Add a 3–4 line professional summary tailored to the target role.")
        if section_scores["experience"] < 80:
            tips.append("Include a Work Experience section with quantified achievements.")
        if section_scores["skills"] < 80:
            tips.append("Add a dedicated Skills section with tools relevant to your target role.")
        if section_scores["action_verbs"] < 60:
            tips.append("Start bullets with strong action verbs (built, led, optimized, shipped).")
        if missing[:5]:
            tips.append(
                "Consider adding role-relevant keywords if truthful: "
                + ", ".join(missing[:5])
                + "."
            )
        if parsed.word_count < 250:
            tips.append("Your resume is short — expand projects/experience with measurable outcomes.")
        if parsed.word_count > 1200:
            tips.append("Tighten wording; keep to ~1–2 pages for ATS-friendly screening.")
        if len(matched) >= 8:
            tips.append("Strong keyword coverage — tailor the top third of the resume to each job posting.")
        return tips

    def _extract_jd_keywords(self, job_description: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]{1,30}", job_description.lower())
        stop = {"with", "and", "the", "for", "you", "our", "will", "have", "this", "that", "from"}
        freq: dict[str, int] = {}
        for tok in tokens:
            if tok in stop or len(tok) < 3:
                continue
            freq[tok] = freq.get(tok, 0) + 1
        ranked = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in ranked[:20]]

    def _llm_suggestions(self, resume_text: str, role: str, missing: list[str]) -> list[str]:
        prompt = (
            "You are an ATS resume coach. Return 4 concise improvement suggestions "
            f"for a {role} candidate. Prefer actionable edits. Missing keywords: {missing}.\n\n"
            f"Resume excerpt:\n{resume_text}\n\n"
            "Respond as a plain numbered list only."
        )
        try:
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.openai_model,
                    "messages": [
                        {"role": "system", "content": "You improve resumes for ATS systems."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 400,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            lines = [re.sub(r"^\d+[\).:-]\s*", "", ln).strip() for ln in content.splitlines()]
            return [ln for ln in lines if len(ln) > 12][:6]
        except Exception as exc:  # noqa: BLE001 — LLM is best-effort
            logger.warning("ats_llm_suggestions_failed", error=str(exc))
            return []
