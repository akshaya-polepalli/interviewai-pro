# AI Coach & study plans (Module 11)

Personalized prep plans and in-app mentoring built on top of Module 8 analytics.

## Why this module exists

Analytics tell candidates *where* they are weak. The coach turns that into:

1. A **multi-day study plan** with concrete tasks and deep links into Coding / Interviews / Resumes.
2. A **short chat** for situational advice (STAR stories, coding cadence, ATS gaps).

Both paths degrade gracefully: plans are fully heuristic; chat uses OpenAI only when `OPENAI_API_KEY` is set.

## Data model

| Table | Purpose |
|-------|---------|
| `study_plans` | One plan per generation (active → archived when replaced) |
| `study_plan_tasks` | Day-offset tasks with category, minutes, `resource_path` |
| `coach_messages` | Persisted user/assistant Q&A |

Statuses: `active` | `completed` (all tasks done) | `archived`.

## Permissions

| Code | Who |
|------|-----|
| `coach:read` | Candidate (insights, plans, history) |
| `coach:write` | Candidate (generate, toggle tasks, ask) |

Re-run seed after deploy so existing roles pick up the new permissions:

```bash
docker compose exec api python -m app.db.seed
```

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/coach/insights` | Headline + tips from analytics |
| GET | `/api/v1/coach/plans` | List plans |
| POST | `/api/v1/coach/plans` | `{ weeks, title?, focus_areas? }` → detail |
| GET | `/api/v1/coach/plans/{id}` | Plan + tasks |
| PATCH | `/api/v1/coach/plans/{id}/tasks/{task_id}` | `{ is_done }` |
| POST | `/api/v1/coach/plans/{id}/archive` | Archive |
| GET | `/api/v1/coach/messages` | Chat history |
| POST | `/api/v1/coach/ask` | `{ message }` → reply + history |

Generating a plan archives prior **active** plans and creates an in-app notification.

## Plan generation algorithm

1. Load analytics (weak topics, skill radar, coding acceptance, interview count).
2. Derive focus categories (`coding`, `algorithms`, `system_design`, `behavioral`, `resume`, `interview`, `general`).
3. Emit `weeks * 7` daily tasks from a curated bank; every 7th day is reflection/report.
4. Optionally prepend a one-sentence OpenAI intro when a key is present.

## Frontend

Route: `/coach` — insights, generate plan, checklist, and coach chat.

## Migration

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```

Revision: `a1c0a7e51100` (after auth tokens).
