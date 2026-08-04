# Publish checklist (Module 16)

Make InterviewAI Pro look intentional on GitHub and in interview conversations.

## Before first push

- [ ] Confirm `.env` is gitignored and never committed
- [ ] `LICENSE` is MIT (change if you need something else)
- [ ] README quick start works on a clean machine
- [ ] `docker compose exec api pytest -q` is green (or document known skips)
- [ ] Demo seed works: `python -m app.db.demo_seed`
- [ ] Replace placeholder author/email in git config only on your machine (never commit secrets)

## Screenshots (recommended)

Capture into `docs/screenshots/` (keep files under ~500KB each):

| File | Shot |
|------|------|
| `01-landing.png` | Landing hero with InterviewAI Pro brand |
| `02-dashboard.png` | Dashboard analytics / streak |
| `03-interview.png` | Mock interview session or feedback |
| `04-voice.png` | Voice interview controls |
| `05-coding.png` | Coding problem editor |
| `06-coach.png` | Study plan checklist |
| `07-roadmaps.png` | Company roadmap weeks |
| `08-billing.png` | Free / Pro / Team cards |

Then uncomment the Screenshots section in the root README.

## GitHub repo settings

1. Create empty repo (no README if this folder already has one).
2. Push:

```powershell
git init
git add .
git commit -m "Initial commit: InterviewAI Pro modules 1-16"
git branch -M main
git remote add origin https://github.com/<you>/interviewai-pro.git
git push -u origin main
```

3. Add topics: `fastapi`, `react`, `typescript`, `postgresql`, `celery`, `interview-prep`, `saas`
4. Pin the repo on your profile
5. Optional: enable GitHub Actions badge once CI is green

## Interview talking points (60 seconds)

1. **Clean architecture** — FastAPI layers (API → service → repository → model)
2. **Async boundary** — Celery for eval / code execution via Redis
3. **AI with fallbacks** — heuristic scoring + optional OpenAI / Whisper
4. **Product surface** — voice interviews, coach, company roadmaps, billing entitlements
5. **Ops** — Docker Compose, prod Nginx profile, CI with Postgres

Architecture diagram: [`docs/system-architecture.md`](system-architecture.md)  
Demo script: [`docs/DEMO.md`](DEMO.md)

## Stubs closed (post Module 16)

| Area | Status |
|------|--------|
| Google / GitHub OAuth | Authorize + callback + SPA `/oauth/callback` |
| Stripe webhook | Signature verify + subscription sync |
| Object storage | Local default; S3/MinIO/R2 via `STORAGE_BACKEND=s3` + boto3 |
| Email | SMTP plain+HTML when `SMTP_HOST` set; console/`debug_token` otherwise |
| Coding languages | Python + JavaScript (Node in API image); Java/C++ intentionally unsupported |
