# Authentication (Module 3)

## Flows

### Register → Verify → Login
1. `POST /api/v1/auth/register` creates user (`pending_verification`) + hashed password + `candidate` role.
2. Email verification token stored as SHA-256 hash only.
3. Dev mode returns `debug_token` when SMTP is unset (never in production).
4. `POST /api/v1/auth/verify-email` marks email verified and status `active`.
5. `POST /api/v1/auth/login` returns access JWT + opaque refresh token.

### Refresh rotation
1. Client sends refresh token.
2. Server validates hash, checks expiry / revocation.
3. Issues new pair and revokes old token (`replaced_by_id` chain).
4. Reuse of a revoked token revokes **all** user refresh tokens (theft signal).

### Password reset
1. `POST /api/v1/auth/forgot-password` always returns the same success message (anti-enumeration).
2. `POST /api/v1/auth/reset-password` updates hash and revokes all sessions.

### OAuth
- `GET /api/v1/auth/oauth/{google|github}/authorize` builds provider URL when client IDs + secrets are set (501 otherwise).
- Callback exchanges the code, upserts/links the user, and redirects to  
  `{FRONTEND_URL}/oauth/callback#access_token=...&refresh_token=...`.
- Register redirect URIs with each provider as  
  `http://localhost:8000/api/v1/auth/oauth/{provider}/callback` (or your public API host).

### Email
- Without `SMTP_HOST`, verification/reset tokens are logged and returned as `debug_token` in development.
- With SMTP configured, plain + HTML messages are sent via STARTTLS.

## Token storage (frontend)
- Access token: in-memory (Axios header).
- Refresh token: `localStorage` (XSS tradeoff documented; HttpOnly cookies are the production upgrade).

## Security checklist encoded
- bcrypt password hashes
- short-lived JWT access tokens
- hashed refresh / verify / reset tokens
- soft RBAC permission helper `require_permissions(...)`
- structured `AppError` JSON responses
