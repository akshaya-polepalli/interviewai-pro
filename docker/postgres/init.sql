-- InterviewAI Pro — Postgres bootstrap
-- Runs once on first volume init via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Application role privileges are managed by the POSTGRES_USER from compose.
-- Schema migrations are owned by Alembic (Module 2).
