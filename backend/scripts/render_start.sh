#!/bin/sh
# Render / PaaS entrypoint: migrate + seed, then serve the API.
set -e

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set. Add your Neon postgres URL in Render → Environment."
  exit 1
fi

if [ -z "${REDIS_URL:-}" ]; then
  echo "ERROR: REDIS_URL is not set. Add your Upstash rediss:// URL in Render → Environment."
  exit 1
fi

echo "Running migrations..."
python -m alembic upgrade head

echo "Seeding roles / coding catalog / demo account..."
python -m app.db.seed
python -m app.db.demo_seed

PORT="${PORT:-8000}"
echo "Starting uvicorn on port ${PORT}..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
