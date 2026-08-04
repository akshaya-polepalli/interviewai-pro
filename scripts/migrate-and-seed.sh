#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
alembic upgrade head
python -m app.db.seed
echo "Migrations + seed complete."
