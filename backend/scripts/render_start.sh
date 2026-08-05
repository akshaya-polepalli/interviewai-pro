#!/bin/sh
# Render / PaaS entrypoint: migrate + seed, then serve the API.
set -e

echo "Running migrations..."
alembic upgrade head

echo "Seeding roles / coding catalog / demo account..."
python -m app.db.seed
python -m app.db.demo_seed

PORT="${PORT:-8000}"
echo "Starting uvicorn on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
