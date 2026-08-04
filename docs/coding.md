# Coding Problems & Submissions (Module 7)

## Flow
1. Seed loads a published problem catalog (`two-sum`, `valid-parentheses`, `max-profit`, `merge-intervals`).
2. Candidate lists problems and opens one (statement + starter code + **public** tests only).
3. `POST /coding/problems/{id}/submissions` runs a restricted Python function harness.
4. Public cases return expected/actual; hidden cases only expose pass/fail status.
5. Optional async path: `sync=false` enqueues `run_submission_task` on Celery.

## Endpoints
- `GET /coding/problems`
- `GET /coding/problems/{id}`
- `GET /coding/problems/by-slug/{slug}`
- `POST /coding/problems/{id}/submissions`
- `GET /coding/submissions`
- `GET /coding/submissions/{id}`

## Runner safety (MVP)
- AST blocklist for dangerous imports (`os`, `subprocess`, …) and builtins (`eval`, `exec`, `open`, …)
- User code written to a temp file; fixed harness imports the entry function
- Per-case subprocess timeout (`time_limit_ms`, default 2000)
- Python and JavaScript runners (`node` required in the API/worker image for JS)
- Java / C++ rejected with a clear error (need a compiler sandbox image)

## Permissions
`coding:read` / `coding:submit` (seeded for candidate & admin)

## UI
- `/coding` — problem list
- `/coding/:id` — editor, run tests, submission history

## Seed
```powershell
docker compose exec api python -m app.db.seed
```
