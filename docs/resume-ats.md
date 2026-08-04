# Resume Upload & ATS (Module 5)

## Flow
1. Client uploads PDF/DOCX/TXT via `POST /api/v1/resumes` (multipart).
2. File is stored through `StorageService` (local now, S3-ready).
3. Text is extracted (`pypdf` / `python-docx`).
4. Heuristic ATS engine scores sections + keyword coverage for a target role.
5. Optional OpenAI suggestions run if `OPENAI_API_KEY` is set.
6. Default upload uses `sync=true` for demo UX; production can set `sync=false` to enqueue Celery.

## Endpoints
- `GET /resumes`
- `POST /resumes`
- `GET /resumes/{id}`
- `POST /resumes/{id}/analyze`
- `GET /resumes/{id}/download`
- `DELETE /resumes/{id}`

## Security
- Auth + `resumes:read` / `resumes:write` permissions
- Extension + content-type validation
- Max upload size (`RESUME_MAX_UPLOAD_MB`, default 5)
- PDF magic-byte check
- Path-traversal-safe storage keys

## UI
`/resumes` — upload, list, ATS report, re-analyze with optional JD, download, delete.
