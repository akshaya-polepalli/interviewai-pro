# Company prep roadmaps (Module 13)

Personalized multi-week tracks for Google, Amazon, Microsoft, Meta, Apple, Netflix, Stripe, OpenAI, and a general path.

## Why this module exists

Generic “practice more” advice does not match how FAANG/startup loops differ. This module encodes:

- Company **interview loop** stages
- Culture / principle hints (e.g. Amazon LPs, Googleyness)
- Week-by-week **milestones** that deep-link into Resumes, Coding, Interviews, Coach, Reports
- **Auto-progress** from real platform activity + optional manual checks

## Data model

| Piece | Role |
|-------|------|
| `company_tracks.py` | Static catalog (milestones, principles, loop) |
| `user_company_roadmaps` | Enrollment, `manual_done[]`, status |

Enrollment is unique per `(user_id, company)`. Enrolling archives other **active** tracks so the UI has one primary focus.

## Auto rules

| Rule | Signal |
|------|--------|
| `ats_70` | Resume ATS ≥ 70 |
| `coding_accepted` | ≥1 accepted submission |
| `interview_done` | Completed/evaluated interview |
| `behavioral_done` | Completed behavioral interview |
| `voice_done` | Voice interview with answers or completed |
| `interview_75` | Interview score ≥ 75 |
| `study_plan` | Active/completed coach study plan |
| `report_ready` | Ready report exists |

## API

| Method | Path |
|--------|------|
| GET | `/api/v1/roadmaps` |
| GET | `/api/v1/roadmaps/{company}` |
| POST | `/api/v1/roadmaps/enroll` `{ company }` |
| POST | `/api/v1/roadmaps/{company}/milestones` `{ milestone_id, is_done }` |
| POST | `/api/v1/roadmaps/{company}/archive` |

Permissions: `roadmaps:read`, `roadmaps:write` (candidate).

## Frontend

Route: `/roadmaps`

## Migration

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
```

Revision: `b2d1c8e62211`.
