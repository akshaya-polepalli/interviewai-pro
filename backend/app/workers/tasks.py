"""Celery task modules."""

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.session import SessionLocal
from app.services.coding_service import CodingService
from app.services.interview_service import InterviewService
from app.services.report_service import ReportService
from app.services.resume_service import ResumeService
from app.workers.celery_app import celery_app

settings = get_settings()
logger = get_logger(__name__)


@celery_app.task(name="app.workers.tasks.ping")
def ping() -> dict[str, str]:
    """Smoke-test task used to verify Celery ↔ Redis connectivity."""
    return {"status": "pong", "service": settings.app_name}


@celery_app.task(
    name="app.workers.tasks.analyze_resume_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def analyze_resume_task(
    self,
    resume_id: str,
    target_role: str | None = None,
    job_description: str | None = None,
) -> dict:
    """Background resume parse + ATS analysis."""
    from uuid import UUID

    db = SessionLocal()
    try:
        service = ResumeService(db)
        analysis = service.process_resume(
            resume_id=UUID(resume_id),
            target_role=target_role,
            job_description=job_description,
        )
        return {
            "resume_id": resume_id,
            "ats_score": str(analysis.ats_score) if analysis.ats_score is not None else None,
            "status": "analyzed",
        }
    except Exception as exc:
        logger.exception("analyze_resume_task_failed", resume_id=resume_id)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.workers.tasks.evaluate_interview_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def evaluate_interview_task(self, interview_id: str) -> dict:
    """Background interview evaluation."""
    from uuid import UUID

    db = SessionLocal()
    try:
        service = InterviewService(db)
        feedback = service.process_evaluation(UUID(interview_id))
        return {
            "interview_id": interview_id,
            "overall_score": str(feedback.overall_score)
            if feedback.overall_score is not None
            else None,
            "status": "evaluated",
        }
    except Exception as exc:
        logger.exception("evaluate_interview_task_failed", interview_id=interview_id)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.workers.tasks.run_submission_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def run_submission_task(self, submission_id: str) -> dict:
    """Background coding submission evaluation."""
    from uuid import UUID

    db = SessionLocal()
    try:
        service = CodingService(db)
        sub = service.process_submission(UUID(submission_id))
        return {
            "submission_id": submission_id,
            "status": sub.status.value if hasattr(sub.status, "value") else str(sub.status),
            "verdict": sub.verdict,
            "score": str(sub.score) if sub.score is not None else None,
        }
    except Exception as exc:
        logger.exception("run_submission_task_failed", submission_id=submission_id)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.workers.tasks.generate_report_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def generate_report_task(self, report_id: str) -> dict:
    """Background report generation."""
    from uuid import UUID

    db = SessionLocal()
    try:
        service = ReportService(db)
        report = service.process_report(UUID(report_id))
        return {
            "report_id": report_id,
            "status": report.status.value
            if hasattr(report.status, "value")
            else str(report.status),
        }
    except Exception as exc:
        logger.exception("generate_report_task_failed", report_id=report_id)
        raise self.retry(exc=exc) from exc
    finally:
        db.close()
