"""
Resume text extraction for PDF / DOCX / TXT.

Parsing is deterministic and local — no LLM required.
AI is reserved for suggestions (optional) in the ATS analyzer.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

from docx import Document
from pypdf import PdfReader

from app.core.exceptions import ValidationAppError


@dataclass
class ParsedResume:
    raw_text: str
    email: str | None = None
    phone: str | None = None
    links: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    word_count: int = 0


EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}")
URL_RE = re.compile(r"https?://[^\s)]+|www\.[^\s)]+|linkedin\.com/[^\s)]+|github\.com/[^\s)]+", re.I)

SECTION_HEADERS = {
    "summary": ("summary", "profile", "objective", "about"),
    "experience": ("experience", "work experience", "employment", "professional experience"),
    "education": ("education", "academics", "academic background"),
    "skills": ("skills", "technical skills", "technologies", "tech stack"),
    "projects": ("projects", "personal projects", "selected projects"),
    "certifications": ("certifications", "certificates", "licenses"),
}


class ResumeParser:
    def parse_bytes(self, *, data: bytes, content_type: str, filename: str) -> ParsedResume:
        text = self._extract_text(data=data, content_type=content_type, filename=filename)
        cleaned = self._normalize(text)
        if len(cleaned.strip()) < 40:
            raise ValidationAppError("Could not extract enough text from the resume")

        email_match = EMAIL_RE.search(cleaned)
        phone_match = PHONE_RE.search(cleaned)
        links = list(dict.fromkeys(URL_RE.findall(cleaned)))[:20]
        sections = self._split_sections(cleaned)
        words = re.findall(r"[A-Za-z0-9']+", cleaned)

        return ParsedResume(
            raw_text=cleaned,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0) if phone_match else None,
            links=links,
            sections=sections,
            word_count=len(words),
        )

    def _extract_text(self, *, data: bytes, content_type: str, filename: str) -> str:
        lower_name = filename.lower()
        if content_type == "application/pdf" or lower_name.endswith(".pdf"):
            return self._from_pdf(data)
        if (
            content_type
            in {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            }
            or lower_name.endswith(".docx")
            or lower_name.endswith(".doc")
        ):
            return self._from_docx(data)
        if content_type.startswith("text/") or lower_name.endswith(".txt"):
            return data.decode("utf-8", errors="ignore")
        raise ValidationAppError(f"Unsupported resume type: {content_type or filename}")

    def _from_pdf(self, data: bytes) -> str:
        reader = PdfReader(io.BytesIO(data))
        chunks: list[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)

    def _from_docx(self, data: bytes) -> str:
        document = Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs if p.text)

    def _normalize(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_sections(self, text: str) -> dict[str, str]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        sections: dict[str, list[str]] = {key: [] for key in SECTION_HEADERS}
        current: str | None = None

        for line in lines:
            lowered = line.lower().strip(":")
            matched_section = None
            for section, aliases in SECTION_HEADERS.items():
                if lowered in aliases or any(lowered.startswith(a) and len(lowered) < 40 for a in aliases):
                    matched_section = section
                    break
            if matched_section:
                current = matched_section
                continue
            if current:
                sections[current].append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items() if v}
