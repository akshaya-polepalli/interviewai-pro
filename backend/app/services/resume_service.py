"""Resume application service — upload, parse, ATS analyze, download, delete."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models import ActivityLog, Resume, ResumeAnalysis
from app.models.enums import ActivityAction, ResumeStatus
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resumes import (
    AnalyzeAcceptedResponse,
    ResumeAnalysisResponse,
    ResumeDetailResponse,
    ResumeResponse,
)
from app.services.ats_analyzer import ATSAnalyzer
from app.services.resume_parser import ResumeParser
from app.services.storage_service import StorageService

logger = get_logger(__name__)


def _status_value(status: ResumeStatus | str) -> str:
    return status.value if hasattr(status, "value") else str(status)


def to_resume_response(resume: Resume, *, include_analysis: bool = True) -> ResumeResponse:
    analysis = None
    if include_analysis and resume.analysis:
        analysis = ResumeAnalysisResponse.model_validate(resume.analysis)
    word_count = None
    if resume.parsed_json and isinstance(resume.parsed_json, dict):
        word_count = resume.parsed_json.get("word_count")
    return ResumeResponse(
        id=resume.id,
        original_filename=resume.original_filename,
        content_type=resume.content_type,
        file_size_bytes=resume.file_size_bytes,
        status=_status_value(resume.status),
        storage_backend=resume.storage_backend,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        word_count=word_count,
        has_analysis=resume.analysis is not None,
        analysis=analysis,
    )


class ResumeService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.resumes = ResumeRepository(db)
        self.storage = StorageService(self.settings)
        self.parser = ResumeParser()
        self.ats = ATSAnalyzer(self.settings)

    def list_mine(self, user_id: UUID) -> list[ResumeResponse]:
        return [to_resume_response(r) for r in self.resumes.list_for_user(user_id)]

    def get_mine(self, user_id: UUID, resume_id: UUID) -> ResumeDetailResponse:
        resume = self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise NotFoundError("Resume not found")
        base = to_resume_response(resume)
        preview = None
        if resume.raw_text:
            preview = resume.raw_text[:1500]
        return ResumeDetailResponse(
            **base.model_dump(),
            raw_text_preview=preview,
            parsed_json=resume.parsed_json,
        )

    def upload(
        self,
        *,
        user_id: UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
        analyze: bool = True,
        sync: bool = False,
        target_role: str | None = None,
    ) -> AnalyzeAcceptedResponse | ResumeResponse:
        self._validate_upload(filename=filename, content_type=content_type, data=data)
        resolved_type = self.storage.guess_content_type(filename, content_type)
        if resolved_type not in self.settings.resume_allowed_types_list:
            # Allow extension-based fallback for browsers that send octet-stream
            if not self._allowed_by_extension(filename):
                raise ValidationAppError(f"Unsupported file type: {resolved_type}")

        key = self.storage.build_resume_key(user_id=str(user_id), filename=filename)
        self.storage.save_bytes(key=key, data=data, content_type=resolved_type)

        resume = Resume(
            user_id=user_id,
            original_filename=filename,
            content_type=resolved_type,
            storage_key=key,
            storage_backend=self.settings.storage_backend,
            file_size_bytes=len(data),
            status=ResumeStatus.UPLOADED,
        )
        self.resumes.create(resume)
        self.db.add(
            ActivityLog(
                user_id=user_id,
                action=ActivityAction.RESUME_UPLOAD,
                resource_type="resume",
                resource_id=str(resume.id),
                metadata_json={"filename": filename, "bytes": len(data)},
            )
        )
        self.db.commit()
        self.db.refresh(resume)

        if not analyze:
            return to_resume_response(resume)

        return self.analyze(
            user_id=user_id,
            resume_id=resume.id,
            target_role=target_role,
            job_description=None,
            sync=sync,
        )

    def analyze(
        self,
        *,
        user_id: UUID,
        resume_id: UUID,
        target_role: str | None,
        job_description: str | None,
        sync: bool,
    ) -> AnalyzeAcceptedResponse:
        resume = self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise NotFoundError("Resume not found")

        resume.status = ResumeStatus.PARSING
        self.resumes.save(resume)
        self.db.commit()

        if sync or self.settings.force_sync_jobs:
            analysis = self.process_resume(
                resume_id=resume.id,
                target_role=target_role,
                job_description=job_description,
            )
            return AnalyzeAcceptedResponse(
                message="Resume analyzed",
                resume_id=resume.id,
                status=ResumeStatus.ANALYZED.value,
                task_id=None,
                analysis=analysis,
            )

        from app.workers.tasks import analyze_resume_task

        async_result = analyze_resume_task.delay(
            str(resume.id),
            target_role,
            job_description,
        )
        return AnalyzeAcceptedResponse(
            message="Resume analysis queued",
            resume_id=resume.id,
            status=ResumeStatus.PARSING.value,
            task_id=async_result.id,
            analysis=None,
        )

    def process_resume(
        self,
        *,
        resume_id: UUID,
        target_role: str | None = None,
        job_description: str | None = None,
    ) -> ResumeAnalysisResponse:
        resume = self.resumes.get_by_id(resume_id)
        if resume is None:
            raise NotFoundError("Resume not found")

        try:
            data = self.storage.read_bytes(key=resume.storage_key)
            parsed = self.parser.parse_bytes(
                data=data,
                content_type=resume.content_type,
                filename=resume.original_filename,
            )
            resume.raw_text = parsed.raw_text
            resume.parsed_json = {
                "email": parsed.email,
                "phone": parsed.phone,
                "links": parsed.links,
                "sections": parsed.sections,
                "word_count": parsed.word_count,
            }
            resume.status = ResumeStatus.PARSED
            self.resumes.save(resume)
            self.db.commit()

            result = self.ats.analyze(
                parsed,
                target_role=target_role,
                job_description=job_description,
            )
            analysis = ResumeAnalysis(
                resume_id=resume.id,
                ats_score=result.ats_score,
                keyword_match_score=result.keyword_match_score,
                matched_keywords=result.matched_keywords,
                missing_keywords=result.missing_keywords,
                suggestions=result.suggestions,
                section_scores=result.section_scores,
                model_provider=result.model_provider,
                model_name=result.model_name,
                raw_response=result.raw_response,
            )
            saved = self.resumes.upsert_analysis(analysis)
            resume.status = ResumeStatus.ANALYZED
            self.resumes.save(resume)
            user_id = resume.user_id
            self.db.commit()
            self.db.refresh(saved)
            from app.services.analytics_service import touch_analytics

            touch_analytics(self.db, user_id)
            logger.info(
                "resume_analyzed",
                resume_id=str(resume.id),
                ats_score=str(result.ats_score),
            )
            return ResumeAnalysisResponse.model_validate(saved)
        except Exception:
            resume.status = ResumeStatus.FAILED
            self.resumes.save(resume)
            self.db.commit()
            logger.exception("resume_analysis_failed", resume_id=str(resume_id))
            raise

    def download(self, user_id: UUID, resume_id: UUID) -> tuple[bytes, str, str]:
        resume = self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise NotFoundError("Resume not found")
        data = self.storage.read_bytes(key=resume.storage_key)
        return data, resume.content_type, resume.original_filename

    def delete(self, user_id: UUID, resume_id: UUID) -> None:
        resume = self.resumes.get_for_user(resume_id, user_id)
        if resume is None:
            raise NotFoundError("Resume not found")
        resume.is_deleted = True
        resume.deleted_at = datetime.now(UTC)
        self.resumes.save(resume)
        try:
            self.storage.delete(key=resume.storage_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("resume_storage_delete_failed", error=str(exc), key=resume.storage_key)
        self.db.commit()

    def _validate_upload(self, *, filename: str, content_type: str | None, data: bytes) -> None:
        if not filename or "." not in filename:
            raise ValidationAppError("Filename must include an extension")
        max_bytes = self.settings.resume_max_upload_mb * 1024 * 1024
        if len(data) == 0:
            raise ValidationAppError("Empty file")
        if len(data) > max_bytes:
            raise ValidationAppError(
                f"File exceeds {self.settings.resume_max_upload_mb}MB limit"
            )
        # Basic PDF magic-byte check when claimed as PDF
        lowered = filename.lower()
        if lowered.endswith(".pdf") and not data.startswith(b"%PDF"):
            raise ValidationAppError("File content is not a valid PDF")

    def _allowed_by_extension(self, filename: str) -> bool:
        lowered = filename.lower()
        return lowered.endswith((".pdf", ".docx", ".doc", ".txt"))
