"""Coding problem / submission schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProgrammingLanguage


class ProblemListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    difficulty: str
    tags: list[str] | None = None
    company_tags: list[str] | None = None
    time_limit_ms: int
    memory_limit_mb: int


class ProblemDetail(ProblemListItem):
    statement_md: str
    starter_code: dict | None = None
    public_tests: list | None = None
    # hidden_tests intentionally omitted


class ExecutionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    test_index: int
    is_hidden: bool
    status: str
    expected_stdout: str | None = None
    actual_stdout: str | None = None
    stderr: str | None = None
    runtime_ms: int | None = None


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    problem_id: UUID
    language: str
    status: str
    verdict: str | None = None
    score: Decimal | None = None
    passed_tests: int | None = None
    total_tests: int | None = None
    runtime_ms: int | None = None
    created_at: datetime
    source_code: str | None = None
    execution_results: list[ExecutionResultResponse] = Field(default_factory=list)


class SubmitCodeRequest(BaseModel):
    source_code: str = Field(min_length=1, max_length=100_000)
    language: ProgrammingLanguage = ProgrammingLanguage.PYTHON
    sync: bool = True
    run_hidden: bool = True


class SubmitAcceptedResponse(BaseModel):
    submission_id: UUID
    status: str
    message: str
    verdict: str | None = None
    score: Decimal | None = None
    passed_tests: int | None = None
    total_tests: int | None = None
