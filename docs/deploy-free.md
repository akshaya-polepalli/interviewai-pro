# Free public deploy (Render + Neon + Upstash)

Make InterviewAI Pro available as a public HTTPS website on free tiers.

> Cold start: after idle time the API may take 30–60 seconds to wake up. That is normal on Render free.

## Architecture

| Piece | Service |
|-------|---------|
| Frontend | Render Static Site → `https://interviewai-pro-web.onrender.com` |
| API | Render Web Service (**Python** free runtime) → `https://interviewai-pro-api.onrender.com` |
| Postgres | [Neon](https://neon.tech) free |
| Redis | [Upstash](https://upstash.com) free |
| Jobs | Inline (`FORCE_SYNC_JOBS=true`) — no Celery worker |

> JavaScript coding problems need Node. On the free Python runtime only **Python** submissions are guaranteed; use Python in the editor for the public demo.


Blueprint: [`render.yaml`](../render.yaml)

## 1. Neon (Postgres)

1. Sign up at https://console.neon.tech
2. Create a project (region close to Render `oregon` if possible).
3. Copy the connection string (URI).
4. Prefer the **pooled** connection string if Neon shows one.
5. Keep it as `postgresql://...` — the API rewrites it to `postgresql+psycopg://` automatically.
6. Ensure SSL is enabled (`sslmode=require` is usually already in Neon URLs).

## 2. Upstash (Redis)

1. Sign up at https://console.upstash.com
2. Create a Redis database (global or US).
3. Copy the **Redis URL** (`rediss://default:...@....upstash.io:6379`).
4. Use the same URL for:
   - `REDIS_URL`
   - `CELERY_BROKER_URL`
   - `CELERY_RESULT_BACKEND`  
   (Celery is unused when `FORCE_SYNC_JOBS=true`, but the readiness probe still needs Redis.)

## 3. Push code to GitHub

The Render blueprint must see `render.yaml` on `main`:

```powershell
git add render.yaml backend/scripts/render_start.sh docs/deploy-free.md .env.example
git add backend/app/core/config.py backend/app/services/*.py backend/Dockerfile README.md
git commit -m "Add free Render deploy (Neon + Upstash, FORCE_SYNC_JOBS)"
git push origin main
```

If CI workflow push is blocked by token scope, push everything except `.github/workflows` first (already done for initial publish).

## 4. Render

1. Sign up at https://render.com with GitHub.
2. **New → Blueprint** → select `akshaya-polepalli/interviewai-pro`.
3. Confirm services from `render.yaml`:
   - `interviewai-pro-api`
   - `interviewai-pro-web`
4. When prompted for sync:false env vars on the API, paste:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Neon URI |
| `REDIS_URL` | Upstash `rediss://...` |
| `CELERY_BROKER_URL` | same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | same as `REDIS_URL` |

5. Deploy. First API build takes several minutes (Docker + Node in image for JS runner).
6. Open:
   - App: https://interviewai-pro-web.onrender.com
   - API health: https://interviewai-pro-api.onrender.com/api/v1/health
   - API docs: https://interviewai-pro-api.onrender.com/docs

## 5. Demo login

After the API finishes its start script (`alembic` + seed + demo seed):

| Account | Password |
|---------|----------|
| `demo@interviewai.local` | `DemoPass1` |
| `admin@example.com` | `AdminPass1` |

## 6. If the frontend cannot call the API

1. Confirm `VITE_API_BASE_URL` on the static site is `https://interviewai-pro-api.onrender.com/api/v1`.
2. Confirm API `CORS_ORIGINS` and `FRONTEND_URL` match the static site origin exactly (no trailing slash).
3. **Rebuild** the static site after changing `VITE_*` (they are bake-time).
4. Wait for a cold start: hit `/api/v1/health` once, then reload the app.

## 7. Resume / LinkedIn tip

Add the live URL next to the project title, e.g.:

`Live demo: https://interviewai-pro-web.onrender.com`

## Limits

- Free services sleep when idle.
- Neon / Upstash free quotas apply.
- No always-on Celery worker (by design on free tier).
- Optional: set `OPENAI_API_KEY` on the API for richer AI answers; heuristic fallbacks work without it.
