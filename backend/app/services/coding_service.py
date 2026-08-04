"""Coding problems application service."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models import ActivityLog, ExecutionResult, Submission
from app.models.enums import ActivityAction, ProgrammingLanguage, SubmissionStatus
from app.repositories.coding_repository import CodingRepository
from app.schemas.coding import (
    ExecutionResultResponse,
    ProblemDetail,
    ProblemListItem,
    SubmissionResponse,
    SubmitAcceptedResponse,
    SubmitCodeRequest,
)
from app.services.code_runner import run_javascript_function_tests, run_python_function_tests

logger = get_logger(__name__)


def _enum_val(value: object | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def to_problem_list_item(p) -> ProblemListItem:
    return ProblemListItem(
        id=p.id,
        slug=p.slug,
        title=p.title,
        difficulty=_enum_val(p.difficulty) or "medium",
        tags=p.tags,
        company_tags=p.company_tags,
        time_limit_ms=p.time_limit_ms,
        memory_limit_mb=p.memory_limit_mb,
    )


def to_problem_detail(p) -> ProblemDetail:
    base = to_problem_list_item(p)
    return ProblemDetail(
        **base.model_dump(),
        statement_md=p.statement_md,
        starter_code=p.starter_code,
        public_tests=p.public_tests,
    )


def to_submission_response(sub: Submission, *, include_source: bool = True) -> SubmissionResponse:
    results = [
        ExecutionResultResponse(
            id=r.id,
            test_index=r.test_index,
            is_hidden=r.is_hidden,
            status=_enum_val(r.status) or "queued",
            expected_stdout=None if r.is_hidden else r.expected_stdout,
            actual_stdout=None if r.is_hidden else r.actual_stdout,
            stderr=None if r.is_hidden else r.stderr,
            runtime_ms=r.runtime_ms,
        )
        for r in sorted(sub.execution_results or [], key=lambda x: x.test_index)
    ]
    return SubmissionResponse(
        id=sub.id,
        problem_id=sub.problem_id,
        language=_enum_val(sub.language) or "python",
        status=_enum_val(sub.status) or "queued",
        verdict=sub.verdict,
        score=sub.score,
        passed_tests=sub.passed_tests,
        total_tests=sub.total_tests,
        runtime_ms=sub.runtime_ms,
        created_at=sub.created_at,
        source_code=sub.source_code if include_source else None,
        execution_results=results,
    )


class CodingService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = CodingRepository(db)

    def list_problems(self) -> list[ProblemListItem]:
        return [to_problem_list_item(p) for p in self.repo.list_published()]

    def get_problem(self, problem_id: UUID) -> ProblemDetail:
        problem = self.repo.get_by_id(problem_id)
        if problem is None or not problem.is_published:
            raise NotFoundError("Problem not found")
        return to_problem_detail(problem)

    def get_problem_by_slug(self, slug: str) -> ProblemDetail:
        problem = self.repo.get_by_slug(slug)
        if problem is None or not problem.is_published:
            raise NotFoundError("Problem not found")
        return to_problem_detail(problem)

    def list_my_submissions(
        self, user_id: UUID, problem_id: UUID | None = None
    ) -> list[SubmissionResponse]:
        return [
            to_submission_response(s)
            for s in self.repo.list_submissions_for_user(user_id, problem_id)
        ]

    def get_my_submission(self, user_id: UUID, submission_id: UUID) -> SubmissionResponse:
        sub = self.repo.get_submission_for_user(submission_id, user_id)
        if sub is None:
            raise NotFoundError("Submission not found")
        return to_submission_response(sub)

    def submit(
        self, user_id: UUID, problem_id: UUID, payload: SubmitCodeRequest
    ) -> SubmitAcceptedResponse | SubmissionResponse:
        problem = self.repo.get_by_id(problem_id)
        if problem is None or not problem.is_published:
            raise NotFoundError("Problem not found")

        if payload.language not in {ProgrammingLanguage.PYTHON, ProgrammingLanguage.JAVASCRIPT}:
            raise ValidationAppError(
                "Only Python and JavaScript are supported. Java/C++ need a sandboxed compiler image."
            )

        source = payload.source_code.strip()
        if not source:
            raise ValidationAppError("Source code is required")

        submission = Submission(
            user_id=user_id,
            problem_id=problem.id,
            language=payload.language,
            source_code=source,
            status=SubmissionStatus.QUEUED,
        )
        self.repo.create_submission(submission)
        self.db.add(
            ActivityLog(
                user_id=user_id,
                action=ActivityAction.CODE_SUBMIT,
                resource_type="coding_problem",
                resource_id=str(problem.id),
                metadata_json={"submission_id": str(submission.id)},
            )
        )
        self.db.commit()

        if not payload.sync:
            from app.workers.tasks import run_submission_task

            task = run_submission_task.delay(str(submission.id))
            submission.celery_task_id = task.id
            self.repo.save_submission(submission)
            self.db.commit()
            return SubmitAcceptedResponse(
                submission_id=submission.id,
                status=SubmissionStatus.QUEUED.value,
                message="Submission queued for evaluation",
            )

        self.process_submission(submission.id)
        self.db.expire_all()
        fresh = self.repo.get_submission_for_user(submission.id, user_id)
        assert fresh is not None
        return to_submission_response(fresh)

    def process_submission(self, submission_id: UUID) -> Submission:
        sub = self.db.get(Submission, submission_id)
        if sub is None:
            raise NotFoundError("Submission not found")
        problem = self.repo.get_by_id(sub.problem_id)
        if problem is None:
            raise NotFoundError("Problem not found")

        sub.status = SubmissionStatus.RUNNING
        self.repo.save_submission(sub)
        self.db.commit()

        starter = problem.starter_code or {}
        entry = starter.get("entry") if isinstance(starter, dict) else None
        if not entry:
            sub.status = SubmissionStatus.SYSTEM_ERROR
            sub.verdict = "missing_entry"
            self.repo.save_submission(sub)
            self.db.commit()
            return sub

        lang = _enum_val(sub.language) or "python"
        if lang == ProgrammingLanguage.JAVASCRIPT.value:
            summary = run_javascript_function_tests(
                source_code=sub.source_code,
                entry=str(entry),
                public_tests=list(problem.public_tests or []),
                hidden_tests=list(problem.hidden_tests or []),
                time_limit_ms=problem.time_limit_ms or 2000,
            )
        elif lang == ProgrammingLanguage.PYTHON.value:
            summary = run_python_function_tests(
                source_code=sub.source_code,
                entry=str(entry),
                public_tests=list(problem.public_tests or []),
                hidden_tests=list(problem.hidden_tests or []),
                time_limit_ms=problem.time_limit_ms or 2000,
            )
        else:
            sub.status = SubmissionStatus.SYSTEM_ERROR
            sub.verdict = "unsupported_language"
            self.repo.save_submission(sub)
            self.db.commit()
            return sub

        if summary.compile_stderr and summary.status == SubmissionStatus.COMPILATION_ERROR:
            sub.status = summary.status
            sub.verdict = summary.verdict
            sub.score = Decimal("0")
            sub.passed_tests = 0
            sub.total_tests = summary.total_tests
            sub.runtime_ms = None
            self.repo.replace_execution_results(
                sub.id,
                [
                    ExecutionResult(
                        submission_id=sub.id,
                        test_index=0,
                        is_hidden=False,
                        status=SubmissionStatus.COMPILATION_ERROR,
                        stderr=summary.compile_stderr,
                    )
                ],
            )
            self.repo.save_submission(sub)
            self.db.commit()
            return sub

        results = [
            ExecutionResult(
                submission_id=sub.id,
                test_index=c.test_index,
                is_hidden=c.is_hidden,
                status=c.status,
                expected_stdout=c.expected_stdout,
                actual_stdout=c.actual_stdout,
                stderr=c.stderr,
                runtime_ms=c.runtime_ms,
            )
            for c in summary.cases
        ]
        self.repo.replace_execution_results(sub.id, results)

        sub.status = summary.status
        sub.verdict = summary.verdict
        sub.score = Decimal(str(summary.score))
        sub.passed_tests = summary.passed_tests
        sub.total_tests = summary.total_tests
        sub.runtime_ms = summary.runtime_ms
        self.repo.save_submission(sub)
        user_id = sub.user_id
        self.db.commit()
        from app.services.analytics_service import touch_analytics

        touch_analytics(self.db, user_id)
        return sub
