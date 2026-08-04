"""PDF report renderer (fpdf2)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fpdf import FPDF


def _safe(text: object) -> str:
    """Core PDF fonts are Latin-1; strip unsupported glyphs cleanly."""
    raw = str(text) if text is not None else ""
    return raw.encode("latin-1", errors="replace").decode("latin-1")


class ProgressReportPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(45, 212, 191)
        self.cell(95, 8, "InterviewAI Pro", align="L")
        self.set_text_color(100, 100, 100)
        self.set_font("Helvetica", "", 9)
        self.cell(95, 8, "Progress Report", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        y = self.get_y()
        self.line(10, y, 200, y)
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def build_progress_pdf(*, title: str, data: dict[str, Any]) -> bytes:
    pdf = ProgressReportPDF(format="A4", unit="mm")
    pdf.set_margins(left=12, top=15, right=12)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    usable = pdf.epw

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(usable, 9, _safe(title))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(usable, 5, _safe(f"Generated {data.get('generated_at', '')}"))
    user = data.get("user") or {}
    pdf.multi_cell(
        usable,
        5,
        _safe(f"Candidate: {user.get('full_name') or '-'} ({user.get('email') or '-'})"),
    )
    pdf.ln(4)

    analytics = data.get("analytics") or {}
    _section(pdf, "Snapshot", usable)
    _bullets(
        pdf,
        usable,
        [
            f"Interviews completed: {analytics.get('completed_interviews', 0)}",
            f"Average interview score: {analytics.get('average_score') or '-'}",
            f"Coding accepted: {analytics.get('coding_accepted', 0)}/"
            f"{analytics.get('coding_submissions', 0)}",
            f"Current streak: {analytics.get('current_streak_days', 0)} days",
            f"Latest ATS: {analytics.get('latest_ats_score') or '-'}",
        ],
    )

    radar = analytics.get("skill_radar") or {}
    _section(pdf, "Skill radar", usable)
    _bullets(
        pdf,
        usable,
        [
            f"{key.title()}: {radar.get(key, 0)}"
            for key in ("technical", "behavioral", "communication", "coding", "resume")
        ],
    )

    roadmap = analytics.get("roadmap") or []
    _section(pdf, "Roadmap", usable)
    _bullets(
        pdf,
        usable,
        [
            f"[{'x' if item.get('done') else ' '}] {item.get('title')}"
            for item in roadmap
        ]
        or ["No roadmap items"],
    )

    unlocked = data.get("unlocked_achievements") or []
    _section(pdf, "Achievements unlocked", usable)
    _bullets(
        pdf,
        usable,
        [f"{a.get('title')} (+{a.get('points', 0)} pts)" for a in unlocked]
        or ["None yet"],
    )

    if data.get("interview"):
        iv = data["interview"]
        _section(pdf, "Interview summary", usable)
        _bullets(
            pdf,
            usable,
            [
                f"Title: {iv.get('title')}",
                f"Type: {iv.get('type')}",
                f"Score: {iv.get('overall_score') or '-'}",
            ],
        )
        if iv.get("summary"):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(usable, 5, _safe(iv["summary"]))
            pdf.ln(2)
        fb = iv.get("feedback") or {}
        if fb.get("strengths"):
            _section(pdf, "Strengths", usable)
            _bullets(pdf, usable, list(fb["strengths"]))
        if fb.get("improvements"):
            _section(pdf, "Improvements", usable)
            _bullets(pdf, usable, list(fb["improvements"]))

    if data.get("resume"):
        rs = data["resume"]
        _section(pdf, "Resume ATS", usable)
        _bullets(
            pdf,
            usable,
            [
                f"File: {rs.get('filename')}",
                f"ATS score: {rs.get('ats_score') or '-'}",
            ],
        )
        if rs.get("suggestions"):
            _section(pdf, "Suggestions", usable)
            _bullets(pdf, usable, list(rs["suggestions"]))

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


def _section(pdf: FPDF, title: str, width: float) -> None:
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 118, 110)
    pdf.cell(width, 8, _safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(45, 212, 191)
    y = pdf.get_y()
    pdf.line(12, y, 70, y)
    pdf.ln(3)


def _bullets(pdf: FPDF, width: float, items: list[str]) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for item in items:
        pdf.multi_cell(width, 5, _safe(f"- {item}"))
    pdf.ln(1)
