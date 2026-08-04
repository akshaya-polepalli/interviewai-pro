"""
Curated question banks for technical, behavioral, and HR interviews.

Used when no LLM key is configured — still production-shaped and role-aware.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import DifficultyLevel, InterviewType, QuestionCategory, TargetCompany, TargetRole


@dataclass(frozen=True)
class BankQuestion:
    prompt: str
    category: QuestionCategory
    difficulty: DifficultyLevel
    expected_points: list[str]
    follow_ups: list[str]


TECHNICAL_BANK: dict[str, list[BankQuestion]] = {
    TargetRole.BACKEND_ENGINEER.value: [
        BankQuestion(
            "Explain how you would design a rate limiter for a public API.",
            QuestionCategory.SYSTEM_DESIGN,
            DifficultyLevel.MEDIUM,
            ["token bucket/leaky bucket", "Redis", "per-user vs per-IP", "burst handling"],
            ["How would you make it distributed across multiple API nodes?"],
        ),
        BankQuestion(
            "Walk through indexing strategies for a PostgreSQL table with heavy read traffic.",
            QuestionCategory.DATABASES,
            DifficultyLevel.MEDIUM,
            ["B-tree vs GIN", "covering indexes", "write amplification", "EXPLAIN ANALYZE"],
            ["When would you avoid adding another index?"],
        ),
        BankQuestion(
            "How do you ensure idempotency for payment or order-creation endpoints?",
            QuestionCategory.BACKEND,
            DifficultyLevel.HARD,
            ["idempotency keys", "dedupe store", "exactly-once vs at-least-once", "retries"],
            ["What happens if the client retries after a timeout?"],
        ),
        BankQuestion(
            "Compare REST and gRPC for internal microservice communication.",
            QuestionCategory.BACKEND,
            DifficultyLevel.EASY,
            ["contracts", "streaming", "latency", "browser support", "tooling"],
            ["Where would you still prefer REST?"],
        ),
        BankQuestion(
            "Describe how Celery/Redis workers improve API responsiveness.",
            QuestionCategory.BACKEND,
            DifficultyLevel.MEDIUM,
            ["async jobs", "broker vs result backend", "retries", "acks late"],
            ["How do you monitor failed jobs in production?"],
        ),
    ],
    TargetRole.FRONTEND_ENGINEER.value: [
        BankQuestion(
            "How do you prevent unnecessary re-renders in a React dashboard?",
            QuestionCategory.FRONTEND,
            DifficultyLevel.MEDIUM,
            ["state colocation", "memoization tradeoffs", "keys", "virtualization"],
            ["When is memoization harmful?"],
        ),
        BankQuestion(
            "Explain client-side routing and protected routes in an SPA.",
            QuestionCategory.FRONTEND,
            DifficultyLevel.EASY,
            ["router", "auth gate", "redirect", "token refresh"],
            ["How do you handle deep links after login?"],
        ),
        BankQuestion(
            "How would you optimize Largest Contentful Paint on a marketing page?",
            QuestionCategory.FRONTEND,
            DifficultyLevel.HARD,
            ["critical CSS", "image priority", "fonts", "bundle splitting"],
            ["Which metric would you monitor in production?"],
        ),
    ],
    TargetRole.SOFTWARE_ENGINEER.value: [
        BankQuestion(
            "Explain time and space complexity of hash maps vs balanced trees.",
            QuestionCategory.DATA_STRUCTURES,
            DifficultyLevel.EASY,
            ["average vs worst case", "ordering", "memory overhead"],
            ["When is a tree preferable despite slower average lookups?"],
        ),
        BankQuestion(
            "Design an in-memory LRU cache.",
            QuestionCategory.ALGORITHMS,
            DifficultyLevel.MEDIUM,
            ["hash map + doubly linked list", "O(1) ops", "eviction", "concurrency"],
            ["How would you persist the cache across process restarts?"],
        ),
        BankQuestion(
            "How do you approach debugging a production incident with elevated 5xx rates?",
            QuestionCategory.OTHER,
            DifficultyLevel.MEDIUM,
            ["metrics", "logs", "traces", "rollback", "blast radius"],
            ["What is your communication plan during the incident?"],
        ),
    ],
    TargetRole.DATA_ANALYST.value: [
        BankQuestion(
            "How do you validate that a dashboard metric matches the source of truth?",
            QuestionCategory.OTHER,
            DifficultyLevel.MEDIUM,
            ["reconciliation", "grain", "filters", "late-arriving data"],
            ["Give an example of a silent metric bug you would catch."],
        ),
        BankQuestion(
            "Explain the difference between INNER JOIN and LEFT JOIN with an example.",
            QuestionCategory.DATABASES,
            DifficultyLevel.EASY,
            ["matching rows", "nulls", "fan-out", "business meaning"],
            ["How can joins inflate counts unexpectedly?"],
        ),
    ],
    TargetRole.ML_ENGINEER.value: [
        BankQuestion(
            "How do you detect and mitigate training-serving skew?",
            QuestionCategory.ML,
            DifficultyLevel.HARD,
            ["feature pipelines", "online/offline parity", "monitoring", "shadow deploy"],
            ["Which metrics would alert you first?"],
        ),
        BankQuestion(
            "Compare precision, recall, and F1 for an imbalanced classification problem.",
            QuestionCategory.ML,
            DifficultyLevel.MEDIUM,
            ["false positives/negatives", "thresholding", "business cost"],
            ["When would you optimize for precision over recall?"],
        ),
    ],
}

BEHAVIORAL_BANK: list[BankQuestion] = [
    BankQuestion(
        "Tell me about a time you disagreed with a teammate. How did you resolve it?",
        QuestionCategory.BEHAVIORAL,
        DifficultyLevel.MEDIUM,
        ["Situation", "Task", "Action", "Result", "collaboration"],
        ["What would you do differently next time?"],
    ),
    BankQuestion(
        "Describe a project where you had ambiguous requirements. How did you proceed?",
        QuestionCategory.BEHAVIORAL,
        DifficultyLevel.MEDIUM,
        ["clarifying questions", "MVP", "stakeholder alignment", "iteration"],
        ["How did you measure success?"],
    ),
    BankQuestion(
        "Give an example of a production mistake you owned. What did you learn?",
        QuestionCategory.BEHAVIORAL,
        DifficultyLevel.HARD,
        ["ownership", "root cause", "prevention", "communication"],
        ["What process change resulted from it?"],
    ),
    BankQuestion(
        "Tell me about a time you mentored someone or raised the team bar.",
        QuestionCategory.BEHAVIORAL,
        DifficultyLevel.MEDIUM,
        ["coaching", "documentation", "feedback", "impact"],
        ["How did you know mentoring was effective?"],
    ),
    BankQuestion(
        "Describe a deadline crunch. How did you prioritize?",
        QuestionCategory.BEHAVIORAL,
        DifficultyLevel.EASY,
        ["tradeoffs", "communication", "scope cut", "quality"],
        ["What did you explicitly choose not to do?"],
    ),
]

HR_BANK: list[BankQuestion] = [
    BankQuestion(
        "Why do you want to join this company and this role?",
        QuestionCategory.HR,
        DifficultyLevel.EASY,
        ["company research", "role fit", "motivation", "impact"],
        ["What would success look like in your first 90 days?"],
    ),
    BankQuestion(
        "What are your salary expectations and how did you arrive at them?",
        QuestionCategory.HR,
        DifficultyLevel.MEDIUM,
        ["market data", "flexibility", "total compensation", "leveling"],
        ["Which parts of the offer matter most besides base salary?"],
    ),
    BankQuestion(
        "Where do you see yourself in 3–5 years?",
        QuestionCategory.HR,
        DifficultyLevel.EASY,
        ["growth", "skills", "leadership vs IC", "alignment"],
        ["How does this role accelerate that path?"],
    ),
    BankQuestion(
        "What is your preferred work style — remote, hybrid, or onsite — and why?",
        QuestionCategory.HR,
        DifficultyLevel.EASY,
        ["collaboration", "focus", "communication habits"],
        ["How do you stay effective asynchronously?"],
    ),
    BankQuestion(
        "Tell me about a time you received critical feedback. How did you respond?",
        QuestionCategory.HR,
        DifficultyLevel.MEDIUM,
        ["receptiveness", "action plan", "follow-up", "growth"],
        ["How do you solicit feedback proactively?"],
    ),
]

COMPANY_FLAVOR: dict[str, str] = {
    TargetCompany.GOOGLE.value: "Emphasize scalability, correctness, and clear problem decomposition.",
    TargetCompany.AMAZON.value: "Emphasize Leadership Principles: ownership, customer obsession, bias for action.",
    TargetCompany.MICROSOFT.value: "Emphasize collaboration, growth mindset, and inclusive design.",
    TargetCompany.META.value: "Emphasize impact, move-fast with quality, and product sense.",
    TargetCompany.NETFLIX.value: "Emphasize judgment, freedom & responsibility, and high talent density.",
    TargetCompany.STRIPE.value: "Emphasize API craftsmanship, reliability, and developer experience.",
    TargetCompany.OPENAI.value: "Emphasize safety, rigorous experimentation, and systems thinking.",
    TargetCompany.GENERAL.value: "Keep answers structured, specific, and measurable.",
}


def pick_questions(
    *,
    interview_type: InterviewType,
    target_role: TargetRole | None,
    count: int,
) -> list[BankQuestion]:
    if interview_type == InterviewType.BEHAVIORAL:
        pool = BEHAVIORAL_BANK
    elif interview_type == InterviewType.HR:
        pool = HR_BANK
    elif interview_type == InterviewType.VOICE:
        role = (target_role or TargetRole.SOFTWARE_ENGINEER).value
        tech = TECHNICAL_BANK.get(role) or TECHNICAL_BANK[TargetRole.SOFTWARE_ENGINEER.value]
        # Spoken rounds mix behavioral storytelling with verbal technical depth.
        pool = []
        for i in range(max(len(BEHAVIORAL_BANK), len(tech))):
            if i < len(BEHAVIORAL_BANK):
                pool.append(BEHAVIORAL_BANK[i])
            if i < len(tech):
                pool.append(tech[i])
    else:
        role = (target_role or TargetRole.SOFTWARE_ENGINEER).value
        pool = TECHNICAL_BANK.get(role) or TECHNICAL_BANK[TargetRole.SOFTWARE_ENGINEER.value]
        # Mix in a general SE question if pool is short
        if len(pool) < count:
            pool = pool + TECHNICAL_BANK[TargetRole.SOFTWARE_ENGINEER.value]

    # Stable rotate for variety without flaky randomness in tests
    seed = (target_role or TargetRole.SOFTWARE_ENGINEER).value
    start = (len(seed) + count) % max(len(pool), 1)
    rotated = pool[start:] + pool[:start]
    return rotated[:count]
