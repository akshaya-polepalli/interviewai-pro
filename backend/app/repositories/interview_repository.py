"""Interview persistence helpers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Answer, Feedback, Interview, Question


class InterviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[Interview]:
        return list(
            self.db.scalars(
                select(Interview)
                .options(
                    selectinload(Interview.questions).selectinload(Question.answers),
                    selectinload(Interview.feedback),
                )
                .where(Interview.user_id == user_id)
                .order_by(Interview.created_at.desc())
            ).all()
        )

    def get_for_user(self, interview_id: UUID, user_id: UUID) -> Interview | None:
        return self.db.scalar(
            select(Interview)
            .options(
                selectinload(Interview.questions).selectinload(Question.answers),
                selectinload(Interview.feedback),
            )
            .where(Interview.id == interview_id, Interview.user_id == user_id)
        )

    def get_by_id(self, interview_id: UUID) -> Interview | None:
        return self.db.scalar(
            select(Interview)
            .options(
                selectinload(Interview.questions).selectinload(Question.answers),
                selectinload(Interview.feedback),
            )
            .where(Interview.id == interview_id)
        )

    def create(self, interview: Interview) -> Interview:
        self.db.add(interview)
        self.db.flush()
        return interview

    def save(self, interview: Interview) -> Interview:
        self.db.add(interview)
        self.db.flush()
        return interview

    def add_question(self, question: Question) -> Question:
        self.db.add(question)
        self.db.flush()
        return question

    def upsert_answer(self, answer: Answer) -> Answer:
        existing = self.db.scalar(
            select(Answer).where(
                Answer.question_id == answer.question_id,
                Answer.user_id == answer.user_id,
            )
        )
        if existing:
            existing.answer_text = answer.answer_text
            existing.transcript = answer.transcript
            existing.audio_storage_key = (
                answer.audio_storage_key
                if answer.audio_storage_key is not None
                else existing.audio_storage_key
            )
            existing.code_snippet = answer.code_snippet
            existing.language = answer.language
            existing.time_spent_seconds = answer.time_spent_seconds
            existing.score = answer.score
            existing.evaluation = answer.evaluation
            self.db.add(existing)
            self.db.flush()
            return existing
        self.db.add(answer)
        self.db.flush()
        return answer

    def upsert_feedback(self, feedback: Feedback) -> Feedback:
        existing = self.db.scalar(
            select(Feedback).where(Feedback.interview_id == feedback.interview_id)
        )
        if existing:
            for field in (
                "overall_score",
                "technical_score",
                "communication_score",
                "confidence_score",
                "star_method_score",
                "strengths",
                "improvements",
                "detailed_feedback",
                "model_provider",
                "model_name",
                "raw_response",
            ):
                setattr(existing, field, getattr(feedback, field))
            self.db.add(existing)
            self.db.flush()
            return existing
        self.db.add(feedback)
        self.db.flush()
        return feedback
