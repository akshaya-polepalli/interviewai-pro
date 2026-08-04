"""Unit tests for resume parser + ATS heuristics (no Postgres required)."""

from app.services.ats_analyzer import ATSAnalyzer
from app.services.resume_parser import ResumeParser


SAMPLE_RESUME = """
Jane Doe
jane.doe@example.com | +1 555-010-2299 | https://linkedin.com/in/janedoe | https://github.com/janedoe

Summary
Backend engineer with 4 years building APIs and data platforms.

Experience
Software Engineer, Acme Corp
- Built FastAPI microservices with PostgreSQL and Redis
- Designed REST APIs and improved latency by 35%
- Implemented CI/CD with Docker and GitHub Actions

Education
B.S. Computer Science, State University

Skills
Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, AWS, SQL, Celery, testing
"""


def test_parser_extracts_contact_and_sections() -> None:
    parsed = ResumeParser().parse_bytes(
        data=SAMPLE_RESUME.encode("utf-8"),
        content_type="text/plain",
        filename="resume.txt",
    )
    assert parsed.email == "jane.doe@example.com"
    assert parsed.word_count > 40
    assert "experience" in parsed.sections
    assert "skills" in parsed.sections


def test_ats_scores_backend_role_highly() -> None:
    parsed = ResumeParser().parse_bytes(
        data=SAMPLE_RESUME.encode("utf-8"),
        content_type="text/plain",
        filename="resume.txt",
    )
    result = ATSAnalyzer().analyze(parsed, target_role="backend_engineer")
    assert float(result.ats_score) >= 70
    assert "python" in [k.lower() for k in result.matched_keywords]
    assert result.suggestions
