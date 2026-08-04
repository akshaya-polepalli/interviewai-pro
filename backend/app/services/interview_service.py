"""Interview application service — create, take, evaluate."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models import ActivityLog, Answer, Feedback, Interview, Question
from app.models.enums import (
    ActivityAction,
    DifficultyLevel,
    InterviewStatus,
    InterviewType,
    TargetCompany,
    TargetRole,
)
from app.repositories.interview_repository import InterviewRepository
from app.schemas.interviews import (
    AnswerResponse,
    CreateInterviewRequest,
    EvaluateAcceptedResponse,
    FeedbackResponse,
    InterviewDetailResponse,
    InterviewResponse,
    QuestionResponse,
    SubmitAnswerRequest,
)
from app.services.interview_evaluator import InterviewEvaluator
from app.services.question_bank import pick_questions
from app.services.speech_service import SpeechService
from app.services.storage_service import StorageService

logger = get_logger(__name__)


def _enum_val(value: object | None) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def to_interview_response(interview: Interview) -> InterviewResponse:
    questions = interview.questions or []
    answered = sum(1 for q in questions if q.answers)
    return InterviewResponse(
        id=interview.id,
        title=interview.title,
        interview_type=_enum_val(interview.interview_type) or "technical",
        status=_enum_val(interview.status) or "draft",
        difficulty=_enum_val(interview.difficulty) or "medium",
        target_role=_enum_val(interview.target_role),
        target_company=_enum_val(interview.target_company),
        overall_score=interview.overall_score,
        summary=interview.summary,
        question_count=len(questions),
        answered_count=answered,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        duration_seconds=interview.duration_seconds,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
    )


def to_detail(interview: Interview) -> InterviewDetailResponse:
    base = to_interview_response(interview)
    questions: list[QuestionResponse] = []
    for q in sorted(interview.questions or [], key=lambda x: x.sequence):
        answers = [
            AnswerResponse(
                id=a.id,
                question_id=a.question_id,
                answer_text=a.answer_text,
                transcript=a.transcript,
                has_audio=bool(a.audio_storage_key),
                code_snippet=a.code_snippet,
                language=a.language,
                time_spent_seconds=a.time_spent_seconds,
                score=a.score,
                evaluation=a.evaluation,
                created_at=a.created_at,
            )
            for a in sorted(q.answers or [], key=lambda a: a.created_at)
        ]
        questions.append(
            QuestionResponse(
                id=q.id,
                sequence=q.sequence,
                category=_enum_val(q.category) or "other",
                difficulty=_enum_val(q.difficulty),
                prompt=q.prompt,
                expected_points=q.expected_points,
                is_follow_up=q.is_follow_up,
                answers=answers,
            )
        )
    feedback = None
    if interview.feedback:
        feedback = FeedbackResponse.model_validate(interview.feedback)
    return InterviewDetailResponse(
        **base.model_dump(),
        questions=questions,
        feedback=feedback,
        config=interview.config,
    )


class InterviewService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = InterviewRepository(db)
        self.storage = StorageService(self.settings)
        self.speech = SpeechService(self.settings)
        self.evaluator = InterviewEvaluator(self.settings)

    def list_mine(self, user_id: UUID) -> list[InterviewResponse]:
        return [to_interview_response(i) for i in self.repo.list_for_user(user_id)]

    def get_mine(self, user_id: UUID, interview_id: UUID) -> InterviewDetailResponse:
        interview = self.repo.get_for_user(interview_id, user_id)
        if interview is None:
            raise NotFoundError("Interview not found")
        return to_detail(interview)

    def create(self, user_id: UUID, payload: CreateInterviewRequest) -> InterviewDetailResponse:
        from app.services.billing_service import BillingService

        itype = payload.interview_type
        BillingService(self.db, self.settings).assert_can_start_interview(
            user_id, voice=itype == InterviewType.VOICE
        )
        role = payload.target_role or TargetRole.SOFTWARE_ENGINEER
        company = payload.target_company or TargetCompany.GENERAL
        title = payload.title or self._default_title(itype, role)

        bank = pick_questions(
            interview_type=itype,
            target_role=role,
            count=payload.question_count,
        )
        interview = Interview(
            user_id=user_id,
            title=title,
            interview_type=itype,
            status=InterviewStatus.DRAFT,
            difficulty=payload.difficulty,
            target_role=role if itype != InterviewType.HR else None,
            target_company=company,
            config={
                "question_count": payload.question_count,
                "source": "question_bank",
                "mode": "voice" if itype == InterviewType.VOICE else "text",
            },
        )
        self.repo.create(interview)

        for idx, bq in enumerate(bank, start=1):
            # Clamp question difficulty toward interview difficulty when bank differs
            diff = bq.difficulty
            if payload.difficulty == DifficultyLevel.EASY and diff == DifficultyLevel.HARD:
                diff = DifficultyLevel.MEDIUM
            self.repo.add_question(
                Question(
                    interview_id=interview.id,
                    sequence=idx,
                    category=bq.category,
                    difficulty=diff,
                    prompt=bq.prompt,
                    expected_points=bq.expected_points,
                    metadata_json={"follow_ups": bq.follow_ups},
                )
            )

        self.db.commit()
        self.db.expire_all()
        fresh = self.repo.get_for_user(interview.id, user_id)
        assert fresh is not None
        return to_detail(fresh)

    def start(self, user_id: UUID, interview_id: UUID) -> InterviewDetailResponse:
        interview = self._owned(user_id, interview_id)
        status = _enum_val(interview.status)
        if status in (
            InterviewStatus.COMPLETED.value,
            InterviewStatus.EVALUATED.value,
            InterviewStatus.ABANDONED.value,
        ):
            raise ConflictError("Interview already finished")
        if status == InterviewStatus.IN_PROGRESS.value:
            return to_detail(interview)

        interview.status = InterviewStatus.IN_PROGRESS
        interview.started_at = datetime.now(UTC)
        self.repo.save(interview)
        self.db.add(
            ActivityLog(
                user_id=user_id,
                action=ActivityAction.INTERVIEW_START,
                resource_type="interview",
                resource_id=str(interview.id),
                metadata_json={"type": _enum_val(interview.interview_type)},
            )
        )
        self.db.commit()
        self.db.expire_all()
        return to_detail(self._owned(user_id, interview_id))

    def submit_answer(
        self, user_id: UUID, interview_id: UUID, payload: SubmitAnswerRequest
    ) -> InterviewDetailResponse:
        interview = self._owned(user_id, interview_id)
        status = _enum_val(interview.status)
        if status == InterviewStatus.DRAFT.value:
            # Auto-start on first answer for smoother UX
            interview.status = InterviewStatus.IN_PROGRESS
            interview.started_at = datetime.now(UTC)
        elif status not in (
            InterviewStatus.IN_PROGRESS.value,
            InterviewStatus.SCHEDULED.value,
        ):
            raise ConflictError("Cannot answer a finished interview")

        question = next((q for q in interview.questions if q.id == payload.question_id), None)
        if question is None:
            raise ValidationAppError("Question does not belong to this interview")

        text = payload.answer_text.strip()
        if not text:
            raise ValidationAppError("Answer text is required")

        self.repo.upsert_answer(
            Answer(
                question_id=question.id,
                user_id=user_id,
                answer_text=text,
                code_snippet=payload.code_snippet,
                language=payload.language,
                time_spent_seconds=payload.time_spent_seconds,
            )
        )
        self.repo.save(interview)
        self.db.commit()
        self.db.expire_all()
        return to_detail(self._owned(user_id, interview_id))

    def submit_voice_answer(
        self,
        user_id: UUID,
        interview_id: UUID,
        *,
        question_id: UUID,
        audio: bytes | None,
        filename: str | None,
        content_type: str | None,
        client_transcript: str | None,
        time_spent_seconds: int | None,
    ) -> InterviewDetailResponse:
        interview = self._owned(user_id, interview_id)
        if _enum_val(interview.interview_type) != InterviewType.VOICE.value:
            raise ValidationAppError("Voice answers are only allowed on voice interviews")

        status = _enum_val(interview.status)
        if status == InterviewStatus.DRAFT.value:
            interview.status = InterviewStatus.IN_PROGRESS
            interview.started_at = datetime.now(UTC)
        elif status not in (
            InterviewStatus.IN_PROGRESS.value,
            InterviewStatus.SCHEDULED.value,
        ):
            raise ConflictError("Cannot answer a finished interview")

        question = next((q for q in interview.questions if q.id == question_id), None)
        if question is None:
            raise ValidationAppError("Question does not belong to this interview")

        audio_key: str | None = None
        provider = "client"
        transcript: str | None = None

        if audio:
            self._validate_audio(
                filename=filename or "answer.webm",
                content_type=content_type,
                data=audio,
            )
            resolved_type = self.storage.guess_content_type(
                filename or "answer.webm", content_type
            )
            audio_key = self.storage.build_audio_key(
                user_id=str(user_id),
                interview_id=str(interview_id),
                filename=filename or "answer.webm",
            )
            self.storage.save_bytes(key=audio_key, data=audio, content_type=resolved_type)
            whisper_text, whisper_provider = self.speech.transcribe(
                audio=audio,
                filename=filename or "answer.webm",
                content_type=resolved_type,
            )
            if whisper_text:
                transcript = whisper_text
                provider = whisper_provider

        if not transcript and client_transcript:
            transcript = client_transcript.strip()
            if provider == "client" and audio_key:
                provider = "client+audio"
            elif not audio_key:
                provider = "client"

        if not transcript:
            raise ValidationAppError(
                "Could not obtain a transcript. Speak clearly, or paste/type your answer text."
            )

        self.repo.upsert_answer(
            Answer(
                question_id=question.id,
                user_id=user_id,
                answer_text=transcript,
                transcript=transcript,
                audio_storage_key=audio_key,
                time_spent_seconds=time_spent_seconds,
                evaluation={"source": "voice", "transcript_provider": provider},
            )
        )
        self.repo.save(interview)
        self.db.commit()
        self.db.expire_all()
        return to_detail(self._owned(user_id, interview_id))

    def get_answer_audio(
        self, user_id: UUID, interview_id: UUID, answer_id: UUID
    ) -> tuple[bytes, str]:
        interview = self._owned(user_id, interview_id)
        for q in interview.questions or []:
            for a in q.answers or []:
                if a.id == answer_id:
                    if not a.audio_storage_key:
                        raise NotFoundError("No audio for this answer")
                    data = self.storage.read_bytes(key=a.audio_storage_key)
                    # Best-effort content type from key extension
                    name = a.audio_storage_key.rsplit("/", 1)[-1].lower()
                    if name.endswith(".wav"):
                        ctype = "audio/wav"
                    elif name.endswith(".mp3"):
                        ctype = "audio/mpeg"
                    elif name.endswith(".ogg"):
                        ctype = "audio/ogg"
                    else:
                        ctype = "audio/webm"
                    return data, ctype
        raise NotFoundError("Answer not found")

    def _validate_audio(self, *, filename: str, content_type: str | None, data: bytes) -> None:
        max_bytes = self.settings.audio_max_upload_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise ValidationAppError(
                f"Audio exceeds {self.settings.audio_max_upload_mb}MB limit"
            )
        if len(data) < 32:
            raise ValidationAppError("Audio file is empty or too small")
        allowed = {
            t.strip().lower()
            for t in self.settings.audio_allowed_content_types.split(",")
            if t.strip()
        }
        resolved = self.storage.guess_content_type(filename, content_type).lower()
        # Browsers often send empty or octet-stream for MediaRecorder blobs
        if resolved in allowed or resolved in {"application/octet-stream", ""}:
            return
        if any(resolved.startswith(a.split("/")[0]) and a.startswith("audio/") for a in allowed):
            return
        raise ValidationAppError(f"Unsupported audio type: {resolved or 'unknown'}")

    def complete(
        self, user_id: UUID, interview_id: UUID, *, evaluate: bool = True, sync: bool = True
    ) -> EvaluateAcceptedResponse | InterviewDetailResponse:
        interview = self._owned(user_id, interview_id)
        status = _enum_val(interview.status)
        if status in (InterviewStatus.EVALUATED.value,):
            return to_detail(interview)
        if status == InterviewStatus.COMPLETED.value and not evaluate:
            return to_detail(interview)

        if status not in (
            InterviewStatus.IN_PROGRESS.value,
            InterviewStatus.DRAFT.value,
            InterviewStatus.COMPLETED.value,
        ):
            raise ConflictError(f"Cannot complete interview in status {status}")

        now = datetime.now(UTC)
        if interview.started_at is None:
            interview.started_at = now
        interview.completed_at = now
        if interview.started_at:
            interview.duration_seconds = max(
                0, int((now - interview.started_at).total_seconds())
            )
        interview.status = InterviewStatus.COMPLETED
        self.repo.save(interview)
        self.db.add(
            ActivityLog(
                user_id=user_id,
                action=ActivityAction.INTERVIEW_COMPLETE,
                resource_type="interview",
                resource_id=str(interview.id),
            )
        )
        self.db.commit()

        if not evaluate:
            self.db.expire_all()
            return to_detail(self._owned(user_id, interview_id))

        if sync:
            return self.evaluate(user_id=user_id, interview_id=interview_id, sync=True)

        from app.workers.tasks import evaluate_interview_task

        evaluate_interview_task.delay(str(interview_id))
        return EvaluateAcceptedResponse(
            interview_id=interview_id,
            status=InterviewStatus.COMPLETED.value,
            message="Interview completed; evaluation queued",
        )

    def evaluate(
        self, user_id: UUID, interview_id: UUID, *, sync: bool = True
    ) -> EvaluateAcceptedResponse:
        interview = self._owned(user_id, interview_id)
        status = _enum_val(interview.status)
        if status not in (
            InterviewStatus.COMPLETED.value,
            InterviewStatus.EVALUATED.value,
            InterviewStatus.IN_PROGRESS.value,
        ):
            raise ConflictError("Interview must be in progress or completed to evaluate")

        if not sync:
            from app.workers.tasks import evaluate_interview_task

            if status == InterviewStatus.IN_PROGRESS.value:
                interview.status = InterviewStatus.COMPLETED
                interview.completed_at = datetime.now(UTC)
                self.repo.save(interview)
                self.db.commit()
            evaluate_interview_task.delay(str(interview_id))
            return EvaluateAcceptedResponse(
                interview_id=interview_id,
                status=_enum_val(interview.status) or "completed",
                message="Evaluation queued",
            )

        result = self.process_evaluation(interview_id)
        return EvaluateAcceptedResponse(
            interview_id=interview_id,
            status=InterviewStatus.EVALUATED.value,
            message="Evaluation complete",
            overall_score=result.overall_score,
        )

    def process_evaluation(self, interview_id: UUID) -> Feedback:
        interview = self.repo.get_by_id(interview_id)
        if interview is None:
            raise NotFoundError("Interview not found")

        items = []
        for q in sorted(interview.questions or [], key=lambda x: x.sequence):
            latest = None
            if q.answers:
                latest = sorted(q.answers, key=lambda a: a.created_at)[-1]
            items.append(
                {
                    "question_id": q.id,
                    "prompt": q.prompt,
                    "expected_points": q.expected_points or [],
                    "answer_text": latest.answer_text if latest else "",
                    "category": _enum_val(q.category),
                    "answer": latest,
                }
            )

        eval_result = self.evaluator.evaluate_interview(
            interview_type=interview.interview_type,
            target_company=_enum_val(interview.target_company),
            items=items,
        )

        for item in items:
            ans = item.get("answer")
            if ans is None:
                continue
            qid = str(item["question_id"])
            ae = eval_result.per_answer.get(qid)
            if ae is None:
                continue
            ans.score = ae.score
            ans.evaluation = {
                "coverage": str(ae.coverage),
                "communication": str(ae.communication),
                "star_score": str(ae.star_score) if ae.star_score is not None else None,
                "matched_points": ae.matched_points,
                "missing_points": ae.missing_points,
                "notes": ae.notes,
            }
            self.db.add(ans)

        feedback = Feedback(
            interview_id=interview.id,
            overall_score=eval_result.overall_score,
            technical_score=eval_result.technical_score,
            communication_score=eval_result.communication_score,
            confidence_score=eval_result.confidence_score,
            star_method_score=eval_result.star_method_score,
            strengths=eval_result.strengths,
            improvements=eval_result.improvements,
            detailed_feedback=eval_result.detailed_feedback,
            model_provider=eval_result.model_provider,
            model_name=eval_result.model_name,
            raw_response=eval_result.raw_response,
        )
        saved = self.repo.upsert_feedback(feedback)

        interview.overall_score = eval_result.overall_score
        interview.summary = eval_result.detailed_feedback[:2000]
        interview.status = InterviewStatus.EVALUATED
        if interview.completed_at is None:
            interview.completed_at = datetime.now(UTC)
        self.repo.save(interview)
        user_id = interview.user_id
        self.db.commit()
        from app.services.analytics_service import touch_analytics

        touch_analytics(self.db, user_id)
        self.db.expire_all()

        refreshed = self.repo.get_by_id(interview_id)
        if refreshed is not None and refreshed.feedback is not None:
            return refreshed.feedback
        return saved

    def delete(self, user_id: UUID, interview_id: UUID) -> None:
        interview = self._owned(user_id, interview_id)
        self.db.delete(interview)
        self.db.commit()

    def _owned(self, user_id: UUID, interview_id: UUID) -> Interview:
        interview = self.repo.get_for_user(interview_id, user_id)
        if interview is None:
            raise NotFoundError("Interview not found")
        return interview

    @staticmethod
    def _default_title(itype: InterviewType, role: TargetRole) -> str:
        label = {
            InterviewType.TECHNICAL: "Technical",
            InterviewType.BEHAVIORAL: "Behavioral",
            InterviewType.HR: "HR",
            InterviewType.CODING: "Coding",
            InterviewType.MIXED: "Mixed",
            InterviewType.VOICE: "Voice",
        }.get(itype, "Mock")
        role_label = role.value.replace("_", " ").title()
        if itype == InterviewType.HR:
            return f"{label} interview"
        return f"{label} interview — {role_label}"
