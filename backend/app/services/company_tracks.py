"""Curated company prep tracks — static catalog, progress computed at runtime."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import TargetCompany


@dataclass(frozen=True)
class MilestoneDef:
    id: str
    title: str
    description: str
    week: int
    category: str
    resource_path: str | None = None
    # Auto-complete when this signal is true (see RoadmapService._signals)
    auto_rule: str | None = None


@dataclass(frozen=True)
class CompanyTrackDef:
    company: str
    name: str
    tagline: str
    weeks: int
    focus: tuple[str, ...]
    interview_loop: tuple[str, ...]
    principles: tuple[str, ...]
    milestones: tuple[MilestoneDef, ...]


def _m(
    mid: str,
    title: str,
    description: str,
    week: int,
    category: str,
    *,
    path: str | None = None,
    rule: str | None = None,
) -> MilestoneDef:
    return MilestoneDef(mid, title, description, week, category, path, rule)


TRACKS: dict[str, CompanyTrackDef] = {
    TargetCompany.GOOGLE.value: CompanyTrackDef(
        company="google",
        name="Google",
        tagline="Correctness, scalability, and clear problem decomposition.",
        weeks=4,
        focus=("algorithms", "system design", "communication"),
        interview_loop=(
            "Phone screen / coding",
            "Onsite coding (2–3)",
            "System design",
            "Googleyness / behavioral",
        ),
        principles=(
            "State assumptions before coding",
            "Optimize after a correct brute force",
            "Discuss tradeoffs explicitly in design",
        ),
        milestones=(
            _m("g_resume", "Polish resume for Google-style impact", "Quantify scope and systems owned.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("g_arrays", "Arrays & hashing drill", "Complete 3 medium array/hash problems.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("g_trees", "Trees & graphs week", "BFS/DFS, topological sort, union-find basics.", 2, "coding", path="/coding"),
            _m("g_mock_tech", "Technical mock interview", "Full technical round with structured answers.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("g_design", "System design sketch", "Design a URL shortener or feed — APIs, storage, scale.", 3, "system_design", path="/interviews"),
            _m("g_voice", "Voice communication pass", "Run a voice mock to practice thinking aloud.", 3, "interview", path="/interviews", rule="voice_done"),
            _m("g_score", "Hit 75+ interview score", "Iterate until feedback shows strong coverage.", 4, "interview", path="/interviews", rule="interview_75"),
            _m("g_coach", "Generate a Google-focused study plan", "Use Coach with focus on algorithms + design.", 4, "general", path="/coach", rule="study_plan"),
        ),
    ),
    TargetCompany.AMAZON.value: CompanyTrackDef(
        company="amazon",
        name="Amazon",
        tagline="Leadership Principles: ownership, customer obsession, bias for action.",
        weeks=4,
        focus=("behavioral STAR", "ownership stories", "coding"),
        interview_loop=(
            "OA coding",
            "Phone / virtual loop",
            "Onsite coding + LP behavioral",
            "Bar raiser",
        ),
        principles=(
            "Map every behavioral answer to 1–2 Leadership Principles",
            "Lead with customer impact and metrics",
            "Show ownership end-to-end, including failures",
        ),
        milestones=(
            _m("a_lp_bank", "Build an LP story bank", "Write STAR stories for Ownership, Dive Deep, Deliver Results, Earn Trust.", 1, "behavioral", path="/interviews"),
            _m("a_resume", "Resume with customer metrics", "Rewrite bullets around customer/business outcomes.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("a_coding", "OA-style coding set", "Get at least one accepted submission under time pressure.", 2, "coding", path="/coding", rule="coding_accepted"),
            _m("a_behavioral", "Behavioral mock (STAR)", "Complete a behavioral interview round.", 2, "behavioral", path="/interviews", rule="behavioral_done"),
            _m("a_tech", "Technical mock", "Practice explaining tradeoffs like a bar raiser expects.", 3, "interview", path="/interviews", rule="interview_done"),
            _m("a_voice", "Voice LP drill", "Speak 2 LP stories under 2 minutes each.", 3, "interview", path="/interviews", rule="voice_done"),
            _m("a_score", "Score 75+ on a mock", "Tighten stories using feedback improvements.", 4, "interview", path="/interviews", rule="interview_75"),
            _m("a_report", "Export a progress report", "Generate a weekly report before onsite week.", 4, "general", path="/reports", rule="report_ready"),
        ),
    ),
    TargetCompany.MICROSOFT.value: CompanyTrackDef(
        company="microsoft",
        name="Microsoft",
        tagline="Growth mindset, collaboration, and inclusive design.",
        weeks=3,
        focus=("coding", "design", "collaboration stories"),
        interview_loop=("Recruiter screen", "Technical phone", "Onsite / virtual loop", "As appropriate: AA"),
        principles=(
            "Show how you learn from feedback",
            "Collaborate across teams without drama",
            "Prefer simple, maintainable designs",
        ),
        milestones=(
            _m("ms_resume", "ATS pass for Microsoft roles", "Upload and hit ATS 70+.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("ms_coding", "Core DSA warm-up", "Land an accepted coding submission.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("ms_collab", "Collaboration STAR story", "Draft a story about unblocking another team.", 2, "behavioral", path="/interviews"),
            _m("ms_mock", "Technical mock", "Complete one technical interview.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("ms_design", "Pragmatic system design", "Design a notification service with clear APIs.", 3, "system_design", path="/interviews"),
            _m("ms_score", "Interview score 75+", "Iterate with Coach tips.", 3, "interview", path="/interviews", rule="interview_75"),
        ),
    ),
    TargetCompany.META.value: CompanyTrackDef(
        company="meta",
        name="Meta",
        tagline="Impact, product sense, and shipping with quality.",
        weeks=4,
        focus=("coding speed", "product sense", "system design"),
        interview_loop=("Coding screen", "Onsite coding", "System design", "Behavioral"),
        principles=(
            "Quantify impact (users, latency, revenue)",
            "Move fast with tests and rollout plans",
            "Product sense: who is the user and what changes?",
        ),
        milestones=(
            _m("meta_coding", "Speed coding reps", "Accepted submission + one timed medium.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("meta_resume", "Impact-heavy resume", "ATS 70+ with user-facing metrics.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("meta_product", "Product sense notes", "Write a 1-pager: metric, user, experiment.", 2, "general", path="/coach"),
            _m("meta_mock", "Technical mock", "Complete a technical interview.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("meta_design", "Feed / chat design", "Design a news feed or messenger slice.", 3, "system_design", path="/interviews"),
            _m("meta_voice", "Voice product pitch", "2-minute spoken product pitch.", 3, "interview", path="/interviews", rule="voice_done"),
            _m("meta_score", "Score 75+", "Close the feedback loop.", 4, "interview", path="/interviews", rule="interview_75"),
            _m("meta_plan", "Coach study plan", "Generate a Meta-focused plan.", 4, "general", path="/coach", rule="study_plan"),
        ),
    ),
    TargetCompany.NETFLIX.value: CompanyTrackDef(
        company="netflix",
        name="Netflix",
        tagline="Judgment, freedom & responsibility, high talent density.",
        weeks=3,
        focus=("judgment stories", "distributed systems", "coding"),
        interview_loop=("Recruiter", "Technical deep dive", "Culture / values", "Hiring manager"),
        principles=(
            "Explain decisions with incomplete data",
            "Own outcomes without blame-shifting",
            "Prefer candor + context over process theater",
        ),
        milestones=(
            _m("nf_resume", "Senior-signal resume", "ATS 70+ with ownership language.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("nf_coding", "Coding baseline", "Accepted coding submission.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("nf_judgment", "Judgment STAR", "Story where you made a hard call with tradeoffs.", 2, "behavioral", path="/interviews", rule="behavioral_done"),
            _m("nf_design", "Streaming / CDN sketch", "Design video delivery or recommendation slice.", 2, "system_design", path="/interviews"),
            _m("nf_mock", "Technical mock", "Complete a technical interview.", 3, "interview", path="/interviews", rule="interview_done"),
            _m("nf_score", "Score 75+", "Tighten communication under feedback.", 3, "interview", path="/interviews", rule="interview_75"),
        ),
    ),
    TargetCompany.STRIPE.value: CompanyTrackDef(
        company="stripe",
        name="Stripe",
        tagline="API craftsmanship, reliability, and developer experience.",
        weeks=3,
        focus=("API design", "reliability", "coding"),
        interview_loop=("Coding", "API / system design", "Integration thinking", "Behavioral"),
        principles=(
            "Design APIs for the integrating developer",
            "Idempotency and failure modes first",
            "Write for clarity — naming is product",
        ),
        milestones=(
            _m("st_resume", "Platform/API resume pass", "ATS 70+.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("st_coding", "Coding baseline", "Accepted submission.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("st_api", "API design drill", "Design idempotent payment/order endpoints.", 2, "system_design", path="/interviews"),
            _m("st_mock", "Technical mock", "Complete a technical interview.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("st_voice", "Explain an API aloud", "Voice round focusing on contracts & errors.", 3, "interview", path="/interviews", rule="voice_done"),
            _m("st_score", "Score 75+", "Iterate with Coach.", 3, "interview", path="/interviews", rule="interview_75"),
        ),
    ),
    TargetCompany.OPENAI.value: CompanyTrackDef(
        company="openai",
        name="OpenAI",
        tagline="Safety, rigorous experimentation, and systems thinking.",
        weeks=4,
        focus=("ML systems", "evaluation rigor", "coding"),
        interview_loop=("Coding", "ML / systems", "Research sense / product", "Behavioral"),
        principles=(
            "Define success metrics before solutions",
            "Discuss failure modes and safety",
            "Separate prototype speed from production reliability",
        ),
        milestones=(
            _m("oai_resume", "ML/systems resume", "ATS 70+.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("oai_coding", "Coding baseline", "Accepted submission.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("oai_eval", "Eval plan write-up", "Write how you'd evaluate a model change.", 2, "general", path="/coach"),
            _m("oai_mock", "Technical mock", "Complete a technical interview.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("oai_design", "LLM app architecture", "Sketch RAG or agent orchestration.", 3, "system_design", path="/interviews"),
            _m("oai_voice", "Voice systems explanation", "Explain tradeoffs out loud.", 3, "interview", path="/interviews", rule="voice_done"),
            _m("oai_score", "Score 75+", "Close feedback gaps.", 4, "interview", path="/interviews", rule="interview_75"),
            _m("oai_plan", "Coach plan", "Generate a study plan.", 4, "general", path="/coach", rule="study_plan"),
        ),
    ),
    TargetCompany.APPLE.value: CompanyTrackDef(
        company="apple",
        name="Apple",
        tagline="Craft, privacy, and end-to-end product ownership.",
        weeks=3,
        focus=("craft", "privacy", "coding"),
        interview_loop=("Coding", "Domain deep dive", "Behavioral / teamwork"),
        principles=(
            "Care about details users feel",
            "Privacy and security by default",
            "Own the full user journey",
        ),
        milestones=(
            _m("ap_resume", "Craft-forward resume", "ATS 70+.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("ap_coding", "Coding baseline", "Accepted submission.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("ap_mock", "Technical mock", "Complete a technical interview.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("ap_behavioral", "Teamwork STAR", "Behavioral round on collaboration.", 2, "behavioral", path="/interviews", rule="behavioral_done"),
            _m("ap_design", "Privacy-aware design", "Design a feature with privacy constraints.", 3, "system_design", path="/interviews"),
            _m("ap_score", "Score 75+", "Iterate.", 3, "interview", path="/interviews", rule="interview_75"),
        ),
    ),
    TargetCompany.GENERAL.value: CompanyTrackDef(
        company="general",
        name="General tech",
        tagline="A balanced prep track when you are still choosing a target.",
        weeks=3,
        focus=("coding", "interviews", "resume"),
        interview_loop=("Recruiter", "Technical", "Behavioral", "Offer"),
        principles=(
            "Consistency beats cramming",
            "Measure progress weekly",
            "Practice aloud, not only in writing",
        ),
        milestones=(
            _m("gen_resume", "Upload & ATS", "Hit ATS 70+.", 1, "resume", path="/resumes", rule="ats_70"),
            _m("gen_coding", "First accepted", "Solve a seeded coding problem.", 1, "coding", path="/coding", rule="coding_accepted"),
            _m("gen_interview", "First mock", "Complete any interview type.", 2, "interview", path="/interviews", rule="interview_done"),
            _m("gen_voice", "Try voice mode", "Complete a voice answer session.", 2, "interview", path="/interviews", rule="voice_done"),
            _m("gen_score", "Score 75+", "Raise quality with feedback.", 3, "interview", path="/interviews", rule="interview_75"),
            _m("gen_coach", "Study plan", "Generate a Coach plan.", 3, "general", path="/coach", rule="study_plan"),
        ),
    ),
}


def list_tracks() -> list[CompanyTrackDef]:
    order = [
        "google",
        "amazon",
        "microsoft",
        "meta",
        "apple",
        "netflix",
        "stripe",
        "openai",
        "general",
    ]
    return [TRACKS[c] for c in order if c in TRACKS]


def get_track(company: str) -> CompanyTrackDef | None:
    return TRACKS.get(company.lower().strip())
