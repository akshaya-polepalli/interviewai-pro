"""
Speech transcription helpers for voice interviews.

Primary path: OpenAI Whisper when OPENAI_API_KEY is set.
Fallback: client-side transcript (Web Speech API) supplied by the SPA.
"""

from __future__ import annotations

import httpx

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpeechService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def transcribe(
        self,
        *,
        audio: bytes,
        filename: str,
        content_type: str,
    ) -> tuple[str | None, str]:
        """
        Returns (transcript_or_none, provider).
        provider is openai|none
        """
        if not audio:
            return None, "none"
        if not self.settings.openai_api_key:
            return None, "none"
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    files={"file": (filename, audio, content_type)},
                    data={"model": self.settings.openai_whisper_model},
                )
                resp.raise_for_status()
                text = (resp.json().get("text") or "").strip()
                return (text or None), "openai"
        except Exception:
            logger.exception("whisper_transcription_failed")
            return None, "none"
