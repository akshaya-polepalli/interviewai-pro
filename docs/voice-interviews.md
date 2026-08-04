# Voice interviews (Module 12)

Spoken mock interviews with browser TTS/STT and optional Whisper transcription.

## Why this module exists

Portfolio standout: most interview-prep demos are text-only. Voice mode exercises:

- Browser media APIs (Mic + MediaRecorder + SpeechSynthesis)
- Optional server-side transcription (OpenAI Whisper)
- Graceful fallback when no API key / no STT support
- Reuse of the existing interview evaluate pipeline

## Architecture

```
Browser TTS  → speaks question
Browser STT  → live transcript (optional)
MediaRecorder → audio/webm blob
     │
     ▼
POST /interviews/{id}/answers/voice  (multipart)
     │
     ├─ store audio via StorageService (audio/{user}/{interview}/…)
     ├─ Whisper if OPENAI_API_KEY set
     └─ else use client transcript
     │
     ▼
Answer.answer_text + Answer.transcript + Answer.audio_storage_key
     │
     ▼
Same heuristic / OpenAI evaluator as text interviews (STAR-aware for voice)
```

## API

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/interviews` | `interview_type: "voice"` |
| POST | `/api/v1/interviews/{id}/answers/voice` | multipart: `question_id`, `transcript?`, `audio?`, `time_spent_seconds?` |
| GET | `/api/v1/interviews/{id}/answers/{answer_id}/audio` | download/play clip |

At least one of **audio** (with Whisper) or **transcript** is required.

## Config

| Env | Default | Purpose |
|-----|---------|---------|
| `AUDIO_MAX_UPLOAD_MB` | 10 | Max clip size |
| `AUDIO_ALLOWED_CONTENT_TYPES` | webm/wav/mpeg/ogg… | MIME allow-list |
| `OPENAI_API_KEY` | — | Enables Whisper |
| `OPENAI_WHISPER_MODEL` | `whisper-1` | Transcription model |

## Frontend

- Create form includes **Voice** type
- Session UI: Speak question → Start answering → edit transcript → Save voice answer
- Chrome/Edge recommended for Web Speech API live captions

## No new migration

`answers.transcript` and `answers.audio_storage_key` already existed from Module 2 schema.
