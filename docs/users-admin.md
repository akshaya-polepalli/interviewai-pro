# Users, RBAC & Admin (Module 4)

## Profile APIs
- `GET /api/v1/users/me` — profile + effective permissions
- `PATCH /api/v1/users/me` — name, bio, target role/company, experience
- `POST /api/v1/users/me/change-password` — rotates password, revokes sessions
- `DELETE /api/v1/users/me` — soft delete (password confirm)
- `GET /api/v1/users/me/sessions` / `DELETE .../sessions/{id}`

## Admin APIs (permission-gated)
- `admin:analytics` → `GET /admin/stats`
- `admin:users` → list/update/delete users
- `admin:access` → list roles & permissions

## Bootstrap admin
Defaults (override with env):
- `SEED_ADMIN_EMAIL=admin@example.com`
- `SEED_ADMIN_PASSWORD=AdminPass1`

```bash
docker compose exec api python -m app.db.seed
```

Then sign in at `/login` and open `/admin`.

## RBAC rule
Authorize on **permission codes** (`admin:users`), not hard-coded role names in services.
Role checks in the UI (`roles.includes("admin")`) are only for navigation convenience.
