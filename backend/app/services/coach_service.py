"""
AI coach: personalized study plans + short mentoring chat.

Plan generation is deterministic from analytics (works offline).
Chat optionally enriches via OpenAI when OPENAI_API_KEY is set.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models import CoachMessage, Notification, StudyPlan, StudyPlanTask
from app.models.enums import (
    CoachMessageRole,
    NotificationChannel,
    NotificationStatus,
    StudyPlanStatus,
)
from app.schemas.coach import (
    CoachAskResponse,
    CoachInsightResponse,
    CoachMessageResponse,
    GenerateStudyPlanRequest,
    StudyPlanDetailResponse,
    StudyPlanResponse,
    StudyPlanTaskResponse,
)
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)

# Rotating task templates keyed by focus category.
_TASK_BANK: dict[str, list[tuple[str, str, int, str]]] = {
    "coding": [
        (
            "Warm-up coding set",
            "Solve 1–2 easy array/hash problems. Aim for clean brute force first, then optimize.",
            35,
            "/coding",
        ),
        (
            "Medium DSA drill",
            "Pick one medium problem. Talk through constraints out loud before coding.",
            45,
            "/coding",
        ),
        (
            "Timed coding sprint",
            "25-minute timer: one problem end-to-end including edge cases and complexity notes.",
            30,
            "/coding",
        ),
    ],
    "algorithms": [
        (
            "Algorithm pattern review",
            "Study one pattern (two pointers, sliding window, or BFS/DFS) and apply it on a problem.",
            40,
            "/coding",
        ),
        (
            "Complexity write-up",
            "After solving, write Big-O for time/space and one alternative approach.",
            25,
            "/coding",
        ),
    ],
    "system_design": [
        (
            "System design sketch",
            "Pick a familiar product and sketch requirements, APIs, and a high-level diagram.",
            40,
            "/interviews",
        ),
        (
            "Trade-off drill",
            "Compare SQL vs NoSQL (or sync vs async) for one concrete use case in writing.",
            30,
            "/interviews",
        ),
    ],
    "behavioral": [
        (
            "STAR story draft",
            "Write one STAR story for conflict, ownership, or failure. Keep it under 2 minutes spoken.",
            30,
            "/interviews",
        ),
        (
            "Behavioral mock",
            "Run a short behavioral interview session and note filler words / structure gaps.",
            35,
            "/interviews",
        ),
    ],
    "resume": [
        (
            "Bullet rewrite",
            "Rewrite 3 resume bullets with metric + action verb. Re-run ATS if you upload a new file.",
            25,
            "/resumes",
        ),
        (
            "Keyword gap pass",
            "Compare your resume to a target JD; add missing skills only if you can defend them.",
            20,
            "/resumes",
        ),
    ],
    "interview": [
        (
            "Technical mock interview",
            "Start a technical mock. Answer in 2–3 minutes each; request feedback after.",
            45,
            "/interviews",
        ),
        (
            "Weak-topic deep dive",
            "Revisit one weak topic from analytics with notes + one follow-up practice question.",
            35,
            "/interviews",
        ),
    ],
    "general": [
        (
            "Weekly reflection",
            "List what improved, what stalled, and one concrete change for next week.",
            20,
            "/dashboard",
        ),
        (
            "Progress report",
            "Generate a weekly progress report to lock in wins and gaps.",
            15,
            "/reports",
        ),
    ],
}


@dataclass
class _PlanDraft:
    title: str
    summary: str
    focus_areas: list[str]
    tasks: list[dict]
    provider: str


class CoachService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.analytics = AnalyticsService(db)

    def insights(self, user_id: UUID) -> CoachInsightResponse:
        bundle = self.analytics.get_bundle(user_id, refresh=False)
        a = bundle.analytics
        weak = list(a.weak_topics or [])
        focus = self._derive_focus(a, override=None)
        tips = self._tips_from_analytics(a, focus)
        weeks = 2 if (a.completed_interviews or 0) < 3 else 3
        headline = (
            f"Focus on {', '.join(focus[:2])} next"
            if focus
            else "Build a steady interview prep rhythm"
        )
        return CoachInsightResponse(
            headline=headline,
            tips=tips,
            weak_topics=weak,
            focus_areas=focus,
            suggested_weeks=weeks,
        )

    def list_plans(self, user_id: UUID) -> list[StudyPlanResponse]:
        rows = list(
            self.db.scalars(
                select(StudyPlan)
                .options(selectinload(StudyPlan.tasks))
                .where(StudyPlan.user_id == user_id)
                .order_by(StudyPlan.created_at.desc())
            ).all()
        )
        return [self._plan_summary(p) for p in rows]

    def get_plan(self, user_id: UUID, plan_id: UUID) -> StudyPlanDetailResponse:
        plan = self._get_plan(user_id, plan_id)
        return self._plan_detail(plan)

    def generate_plan(
        self, user_id: UUID, payload: GenerateStudyPlanRequest
    ) -> StudyPlanDetailResponse:
        from app.services.billing_service import BillingService

        BillingService(self.db).assert_can_use_coach(user_id)
        # Archive previous active plans so the UI has one clear "current" plan.
        active = list(
            self.db.scalars(
                select(StudyPlan).where(
                    StudyPlan.user_id == user_id,
                    StudyPlan.status == StudyPlanStatus.ACTIVE,
                )
            ).all()
        )
        for plan in active:
            plan.status = StudyPlanStatus.ARCHIVED
            self.db.add(plan)

        draft = self._build_plan_draft(user_id, payload)
        plan = StudyPlan(
            user_id=user_id,
            title=draft.title,
            summary=draft.summary,
            status=StudyPlanStatus.ACTIVE,
            weeks=payload.weeks,
            focus_areas=draft.focus_areas,
            model_provider=draft.provider,
        )
        self.db.add(plan)
        self.db.flush()

        for item in draft.tasks:
            self.db.add(
                StudyPlanTask(
                    plan_id=plan.id,
                    sequence=item["sequence"],
                    day_offset=item["day_offset"],
                    title=item["title"],
                    description=item["description"],
                    category=item["category"],
                    estimated_minutes=item["estimated_minutes"],
                    resource_path=item["resource_path"],
                    is_done=False,
                )
            )

        self.db.add(
            Notification(
                user_id=user_id,
                title="Study plan ready",
                body=f"Your plan “{plan.title}” is ready — {len(draft.tasks)} tasks across {payload.weeks} week(s).",
                channel=NotificationChannel.IN_APP,
                status=NotificationStatus.SENT,
                payload={"plan_id": str(plan.id), "type": "study_plan"},
                sent_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        return self.get_plan(user_id, plan.id)

    def update_task(
        self, user_id: UUID, plan_id: UUID, task_id: UUID, *, is_done: bool
    ) -> StudyPlanDetailResponse:
        plan = self._get_plan(user_id, plan_id)
        task = next((t for t in plan.tasks if t.id == task_id), None)
        if task is None:
            raise NotFoundError("Task not found")
        task.is_done = is_done
        self.db.add(task)

        if plan.tasks and all(t.is_done for t in plan.tasks):
            plan.status = StudyPlanStatus.COMPLETED
            self.db.add(plan)

        self.db.commit()
        return self.get_plan(user_id, plan_id)

    def archive_plan(self, user_id: UUID, plan_id: UUID) -> StudyPlanDetailResponse:
        plan = self._get_plan(user_id, plan_id)
        plan.status = StudyPlanStatus.ARCHIVED
        self.db.add(plan)
        self.db.commit()
        return self.get_plan(user_id, plan_id)

    def list_messages(self, user_id: UUID, *, limit: int = 40) -> list[CoachMessageResponse]:
        rows = list(
            self.db.scalars(
                select(CoachMessage)
                .where(CoachMessage.user_id == user_id)
                .order_by(CoachMessage.created_at.desc())
                .limit(limit)
            ).all()
        )
        rows.reverse()
        return [self._msg(m) for m in rows]

    def ask(self, user_id: UUID, message: str) -> CoachAskResponse:
        from app.services.billing_service import BillingService

        BillingService(self.db).assert_can_use_coach(user_id)
        text = message.strip()
        if not text:
            raise ValidationAppError("Message cannot be empty")

        user_msg = CoachMessage(
            user_id=user_id,
            role=CoachMessageRole.USER,
            content=text,
        )
        self.db.add(user_msg)
        self.db.flush()

        insight = self.insights(user_id)
        reply_text, provider = self._coach_reply(text, insight)
        assistant = CoachMessage(
            user_id=user_id,
            role=CoachMessageRole.ASSISTANT,
            content=reply_text,
            extra={"provider": provider},
        )
        self.db.add(assistant)
        self.db.commit()

        history = self.list_messages(user_id)
        return CoachAskResponse(reply=self._msg(assistant), history=history)

    # ----- internals -----

    def _get_plan(self, user_id: UUID, plan_id: UUID) -> StudyPlan:
        plan = self.db.scalar(
            select(StudyPlan)
            .options(selectinload(StudyPlan.tasks))
            .where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
        )
        if plan is None:
            raise NotFoundError("Study plan not found")
        return plan

    def _build_plan_draft(
        self, user_id: UUID, payload: GenerateStudyPlanRequest
    ) -> _PlanDraft:
        bundle = self.analytics.get_bundle(user_id, refresh=False)
        a = bundle.analytics
        focus = self._derive_focus(a, override=payload.focus_areas)
        title = payload.title or f"{payload.weeks}-week interview prep plan"
        summary_bits = [
            f"Personalized for your current analytics ({a.completed_interviews or 0} interviews done).",
        ]
        if a.weak_topics:
            summary_bits.append(f"Weak topics: {', '.join(a.weak_topics[:4])}.")
        summary_bits.append(f"Primary focus: {', '.join(focus)}.")

        days = payload.weeks * 7
        tasks: list[dict] = []
        seq = 1
        for day in range(days):
            # Rest rhythm: every 7th day is reflection.
            if day > 0 and (day + 1) % 7 == 0:
                category = "general"
            else:
                category = focus[day % len(focus)]
            bank = _TASK_BANK.get(category) or _TASK_BANK["general"]
            title_t, desc, mins, path = bank[day % len(bank)]
            if category in {"algorithms", "system_design"} and a.weak_topics:
                weak = a.weak_topics[day % len(a.weak_topics)]
                desc = f"{desc} Emphasize: {weak}."
            tasks.append(
                {
                    "sequence": seq,
                    "day_offset": day,
                    "title": f"Day {day + 1}: {title_t}",
                    "description": desc,
                    "category": category,
                    "estimated_minutes": mins,
                    "resource_path": path,
                }
            )
            seq += 1

        provider = "heuristic"
        if self.settings.openai_api_key:
            enriched = self._openai_plan_summary(title, focus, a.weak_topics or [], payload.weeks)
            if enriched:
                summary_bits.insert(0, enriched)
                provider = "openai+heuristic"

        return _PlanDraft(
            title=title,
            summary=" ".join(summary_bits),
            focus_areas=focus,
            tasks=tasks,
            provider=provider,
        )

    def _derive_focus(self, analytics, override: list[str] | None) -> list[str]:
        if override:
            cleaned = [self._normalize_focus(x) for x in override if x.strip()]
            cleaned = [c for c in cleaned if c]
            if cleaned:
                return list(dict.fromkeys(cleaned))[:5]

        focus: list[str] = []
        weak = [str(w).lower() for w in (analytics.weak_topics or [])]
        radar = analytics.skill_radar
        radar_dict: dict = {}
        if radar is not None:
            if hasattr(radar, "model_dump"):
                radar_dict = radar.model_dump()
            elif isinstance(radar, dict):
                radar_dict = radar
        if radar_dict:
            numeric = [
                (k, float(v))
                for k, v in radar_dict.items()
                if isinstance(v, (int, float))
            ]
            numeric.sort(key=lambda x: x[1])
            for key, _ in numeric[:3]:
                focus.append(self._normalize_focus(key))

        for w in weak:
            focus.append(self._normalize_focus(w))

        coding_acc = 0.0
        total = analytics.coding_submissions or 0
        if total:
            coding_acc = (analytics.coding_accepted or 0) / total
        if coding_acc < 0.5 or total < 3:
            focus.append("coding")

        if (analytics.completed_interviews or 0) < 2:
            focus.append("interview")

        focus = [f for f in focus if f]
        if not focus:
            focus = ["coding", "interview", "behavioral"]
        # Always keep a reflection bucket available via rotation.
        ordered = list(dict.fromkeys(focus))
        if "general" not in ordered:
            ordered.append("general")
        return ordered[:5]

    @staticmethod
    def _normalize_focus(raw: str) -> str:
        key = raw.strip().lower().replace("-", " ").replace("_", " ")
        aliases = {
            "coding": "coding",
            "algorithms": "algorithms",
            "algorithm": "algorithms",
            "data structures": "algorithms",
            "dsa": "algorithms",
            "system design": "system_design",
            "systems": "system_design",
            "behavioral": "behavioral",
            "behavior": "behavioral",
            "resume": "resume",
            "ats": "resume",
            "interview": "interview",
            "technical": "interview",
            "general": "general",
        }
        for token, mapped in aliases.items():
            if token in key or key == token:
                return mapped
        if key in _TASK_BANK:
            return key
        return "interview"

    def _tips_from_analytics(self, a, focus: list[str]) -> list[str]:
        tips: list[str] = []
        if a.weak_topics:
            tips.append(f"Double down on: {', '.join(a.weak_topics[:3])}.")
        if (a.coding_submissions or 0) == 0:
            tips.append("Submit at least one coding problem this week to unlock streak signals.")
        elif (a.coding_accepted or 0) == 0:
            tips.append("Debug one failed submission carefully — accepted > volume.")
        if (a.completed_interviews or 0) == 0:
            tips.append("Run a short technical mock to baseline communication + correctness.")
        if (a.current_streak_days or 0) < 3:
            tips.append("Aim for a 3-day streak: short daily sessions beat weekend cramming.")
        if not tips:
            tips.append(f"Keep rotating focus areas: {', '.join(focus[:3])}.")
        return tips[:5]

    def _coach_reply(self, message: str, insight: CoachInsightResponse) -> tuple[str, str]:
        if self.settings.openai_api_key:
            llm = self._openai_chat(message, insight)
            if llm:
                return llm, "openai"
        return self._heuristic_reply(message, insight), "heuristic"

    def _heuristic_reply(self, message: str, insight: CoachInsightResponse) -> str:
        lower = message.lower()
        tips = "\n".join(f"- {t}" for t in insight.tips[:3])
        focus = ", ".join(insight.focus_areas[:3]) or "coding + interviews"

        if any(w in lower for w in ("plan", "schedule", "week", "study")):
            return (
                f"{insight.headline}.\n\n"
                f"I recommend a **{insight.suggested_weeks}-week** plan focused on {focus}. "
                f"Generate a plan from the Coach page and check off daily tasks.\n\n"
                f"Quick tips:\n{tips}"
            )
        if any(w in lower for w in ("coding", "leetcode", "algorithm", "dsa")):
            return (
                "For coding: warm up easy → one medium under a timer → write complexity notes. "
                "Use the Coding lab and mark tasks done in your study plan.\n\n"
                f"Your focus areas right now: {focus}."
            )
        if any(w in lower for w in ("resume", "ats", "cv")):
            return (
                "Resume tip: every bullet needs action + scope + metric. "
                "Upload a fresh PDF on Resumes and chase the ATS gaps before more applications."
            )
        if any(w in lower for w in ("behavioral", "star", "story")):
            return (
                "Behavioral: draft STAR stories for ownership, conflict, failure, and impact. "
                "Speak each in under two minutes, then run a behavioral mock interview."
            )
        if insight.weak_topics:
            return (
                f"{insight.headline}.\n\n"
                f"Your analytics flag: {', '.join(insight.weak_topics)}. "
                f"Prioritize those in mocks and coding drills.\n\nTips:\n{tips}"
            )
        return (
            f"{insight.headline}.\n\n"
            f"Focus on {focus}. Ask me about coding, resumes, behavioral stories, "
            f"or generating a multi-week plan.\n\nTips:\n{tips}"
        )

    def _openai_chat(self, message: str, insight: CoachInsightResponse) -> str | None:
        system = (
            "You are InterviewAI Pro's concise interview coach. "
            "Give practical, structured advice in under 180 words. "
            "Use the candidate's analytics context. No fluff."
        )
        context = (
            f"Headline: {insight.headline}\n"
            f"Weak topics: {', '.join(insight.weak_topics) or 'none'}\n"
            f"Focus: {', '.join(insight.focus_areas)}\n"
            f"Tips: {'; '.join(insight.tips)}"
        )
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json={
                        "model": self.settings.openai_model,
                        "temperature": 0.4,
                        "messages": [
                            {"role": "system", "content": system},
                            {
                                "role": "user",
                                "content": f"Context:\n{context}\n\nCandidate question:\n{message}",
                            },
                        ],
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                return content or None
        except Exception:
            logger.exception("coach_openai_chat_failed")
            return None

    def _openai_plan_summary(
        self, title: str, focus: list[str], weak: list[str], weeks: int
    ) -> str | None:
        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json={
                        "model": self.settings.openai_model,
                        "temperature": 0.3,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Write one motivating sentence (max 40 words) for a study plan intro.",
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Title: {title}. Weeks: {weeks}. "
                                    f"Focus: {', '.join(focus)}. Weak: {', '.join(weak) or 'general prep'}."
                                ),
                            },
                        ],
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip() or None
        except Exception:
            logger.warning("coach_openai_plan_summary_failed")
            return None

    def _plan_summary(self, plan: StudyPlan) -> StudyPlanResponse:
        tasks = plan.tasks or []
        return StudyPlanResponse(
            id=plan.id,
            title=plan.title,
            summary=plan.summary,
            status=_enum_val(plan.status),
            weeks=plan.weeks,
            focus_areas=plan.focus_areas,
            model_provider=plan.model_provider,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            task_count=len(tasks),
            done_count=sum(1 for t in tasks if t.is_done),
        )

    def _plan_detail(self, plan: StudyPlan) -> StudyPlanDetailResponse:
        base = self._plan_summary(plan)
        tasks = sorted(plan.tasks or [], key=lambda t: (t.day_offset, t.sequence))
        return StudyPlanDetailResponse(
            **base.model_dump(),
            tasks=[StudyPlanTaskResponse.model_validate(t) for t in tasks],
        )

    @staticmethod
    def _msg(row: CoachMessage) -> CoachMessageResponse:
        return CoachMessageResponse(
            id=row.id,
            role=_enum_val(row.role),
            content=row.content,
            extra=row.extra,
            created_at=row.created_at,
        )


def _enum_val(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)
