# Architecture Overview

InterviewAI Pro is a production-shaped monorepo for AI interview prep.

For diagrams and end-to-end topology (Modules 1–16), see **[`system-architecture.md`](system-architecture.md)**.

## Goals

- HTTP API (FastAPI)
- SPA (React + Vite)
- Relational DB (PostgreSQL)
- Cache / broker (Redis)
- Async workers (Celery)
- Reverse proxy (Nginx, prod profile)
- Optional AI (OpenAI) and payments (Stripe) with offline fallbacks

## Request path (development)

1. Browser loads Vite SPA on `:5173`.
2. SPA calls `VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).
3. FastAPI validates input, runs services, returns JSON.
4. Long-running work is enqueued to Celery via Redis (interview eval, code execution).

## Backend layering

| Layer | Folder | Responsibility |
|-------|--------|----------------|
| Transport | `app/api` | HTTP routes, status codes, OpenAPI |
| Application | `app/services` | Business use-cases |
| Persistence | `app/repositories` | SQLAlchemy queries |
| Domain | `app/models`, `app/schemas` | Entities + DTOs |
| Infrastructure | `app/database`, `app/workers`, storage, AI clients | External systems |
| Cross-cutting | `app/core`, `app/middleware`, `app/dependencies` | Config, auth, logging |

## Health vs readiness

- **Liveness** (`/api/v1/health`): process is up.
- **Readiness** (`/api/v1/ready`): Postgres + Redis respond. Load balancers use this to stop sending traffic when deps fail.
