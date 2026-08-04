# Reports & Notifications (Module 9)

## Flow
1. Client creates a report via `POST /api/v1/reports` (type + **pdf** / markdown / json).
2. Service refreshes analytics, builds a payload, writes a file via `StorageService`.
3. Report status becomes `ready`; an in-app notification is created.
4. Client downloads via `GET /reports/{id}/download` or deletes the report.

Default format is **PDF** (`application/pdf`).

## Report types
- `weekly_progress` / `monthly_progress`
- `roadmap`
- `resume_ats` (latest or specific resume)
- `interview_summary` (requires `interview_id`)

## Endpoints
### Reports
- `GET /reports`
- `POST /reports`
- `GET /reports/{id}`
- `GET /reports/{id}/download`
- `DELETE /reports/{id}`

### Notifications
- `GET /notifications`
- `POST /notifications/{id}/read`

## Async
`sync=false` enqueues `generate_report_task`.

## UI
`/reports` — generate, list, download, notifications

## Permissions
`reports:read` for reports; `users:read` for notifications
