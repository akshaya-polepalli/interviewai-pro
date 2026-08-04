# AI Mock Interviews (Module 6)

## Flow
1. Client creates an interview via `POST /api/v1/interviews` (type, role, company, difficulty, count).
2. Question bank fills role-aware technical / behavioral / HR prompts (LLM optional later).
3. Candidate starts the session, submits answers per question.
4. `POST /interviews/{id}/complete?evaluate=true&sync=true` runs heuristic scoring (+ OpenAI enrich if keyed).
5. Feedback stores overall / content / communication / confidence / STAR scores with strengths & improvements.

## Endpoints
- `GET /interviews`
- `POST /interviews`
- `GET /interviews/{id}`
- `POST /interviews/{id}/start`
- `POST /interviews/{id}/answers`
- `POST /interviews/{id}/answers/voice` — voice mode (Module 12)
- `GET /interviews/{id}/answers/{answer_id}/audio`
- `POST /interviews/{id}/complete`
- `POST /interviews/{id}/evaluate`
- `DELETE /interviews/{id}`

## Scoring (offline-first)
- **Content**: coverage of `expected_points`
- **Communication**: length band, sentence structure, filler penalty
- **STAR**: for behavioral/HR/voice (Situation → Task → Action → Result)
- **Confidence**: completion rate + concreteness (numbers / outcomes)
- Optional: `OPENAI_API_KEY` rewrites coaching narrative

## Voice (Module 12)
See [`docs/voice-interviews.md`](voice-interviews.md).
## Background jobs
`evaluate_interview_task` — use `sync=false` on complete/evaluate to enqueue Celery.

## UI
- `/interviews` — create + list
- `/interviews/:id` — answer questions + view feedback

## Permissions
`interviews:read` / `interviews:write` (seeded for candidate & admin roles)
