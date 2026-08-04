# Demo walkthrough (Module 14)

Use this script when showing InterviewAI Pro in interviews or on a screen recording.

## 1. Boot

```powershell
cp .env.example .env
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
docker compose exec api python -m app.db.demo_seed
```

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | SPA |
| http://localhost:8000/docs | OpenAPI |
| http://localhost:8000/api/v1/health | Liveness |

## 2. Accounts

| Email | Password | Role |
|-------|----------|------|
| `demo@interviewai.local` | `DemoPass1` | Candidate (sample data) |
| `admin@example.com` | `AdminPass1` | Admin (if seed admin enabled) |

Override via `.env`: `SEED_DEMO_EMAIL`, `SEED_DEMO_PASSWORD`, `SEED_DEMO_ENABLED`.

## 3. Five-minute tour

1. **Landing** — brand + module grid + demo CTA  
2. **Login** as demo → **Dashboard** (streak, radar, roadmap chips)  
3. **Interviews** — open *Demo Technical Round* feedback; create a **Voice** round  
4. **Coding** — Two Sum (demo already has an accepted submission)  
5. **Coach** — view seeded study plan or generate a new one (demo is on **Pro**)  
6. **Roadmaps** — Google track enrolled; watch auto milestones  
7. **Billing** — Free / Pro / Team; local upgrade without Stripe  
8. **Reports** — generate a weekly PDF  
9. **Admin** (admin user) — platform stats  

## 4. Talking points (system design)

- Layered FastAPI (API → services → repositories → models)
- JWT + refresh rotation + RBAC permissions
- Celery for interview eval / code execution
- Local object storage with S3-shaped interface
- Heuristic AI with optional OpenAI enrichment (interviews, ATS, Whisper, coach)
- Prod compose: Nginx gateway, multi-stage images, CI with Postgres

## 5. Reset demo data

Re-run `python -m app.db.demo_seed` — it upserts the demo user and skips duplicate sample rows.
