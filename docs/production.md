# Production deployment (Module 10)

## Goals
Ship a production-shaped stack: no hot-reload, static SPA, reverse proxy, rate limits, CI with Postgres.

## Dev vs prod

| | Development | Production |
|--|-------------|------------|
| Compose file | `docker-compose.yml` | `docker-compose.prod.yml` |
| Frontend | Vite HMR `:5173` | Nginx static `:80` via gateway |
| API | uvicorn `--reload` | uvicorn `--workers 2` |
| Source mounts | yes | no (image only) |
| Entry URL | http://localhost:5173 | http://localhost |

## Bring up production stack

```powershell
cp .env.example .env
# Set SECRET_KEY to a long random value
# APP_ENV=production
# APP_DEBUG=false

docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python -m app.db.seed
```

Open http://localhost (gateway nginx). API docs: http://localhost/docs

Stop:

```powershell
docker compose -f docker-compose.prod.yml down
```

## Gateway behavior (`docker/nginx/nginx.prod.conf`)
- `/api/` → FastAPI (rate limited)
- `/api/v1/auth/login|register|…` → stricter rate limit
- `/` → frontend static container
- Security headers: `X-Frame-Options`, `nosniff`, `Referrer-Policy`
- SPA uses same-origin `VITE_API_BASE_URL=/api/v1`

## CI
- Unit job: pure logic tests without Postgres
- Integration job: Postgres + Redis services, migrate, seed, full pytest
- Frontend: typecheck, vitest, production build
- Compose: validates both `docker-compose.yml` and `docker-compose.prod.yml`

## Checklist before real deploy
- [ ] Rotate `SECRET_KEY`
- [ ] Strong Postgres password
- [ ] TLS terminator (Cloudflare / ALB / Caddy) in front of nginx
- [ ] Backups for Postgres volume
- [ ] Set `OPENAI_API_KEY` only if you want LLM enrichment
- [ ] Review CORS origins for your public domain
