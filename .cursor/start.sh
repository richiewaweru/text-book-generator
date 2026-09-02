#!/usr/bin/env bash
# Per-boot runtime initialization. Starts PostgreSQL, ensures the application
# role/database exist, and applies database migrations. Must be idempotent and
# must return (the long-running dev servers live in `terminals`).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.local/bin:$PATH"

log() { printf '\n[start] %s\n' "$*"; }

# --- Start PostgreSQL -------------------------------------------------------
log "Starting PostgreSQL cluster"
sudo pg_ctlcluster 16 main start 2>/dev/null || true

# Wait until Postgres accepts connections.
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then break; fi
  sleep 1
done

# --- Ensure role + database -------------------------------------------------
log "Ensuring application role and database"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='textbook') THEN
    CREATE ROLE textbook LOGIN PASSWORD 'textbook';
  END IF;
END $$;
SQL
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='textbook_agent'" | grep -q 1; then
  sudo -u postgres createdb -O textbook textbook_agent
fi

# --- Apply migrations -------------------------------------------------------
log "Applying database migrations (alembic upgrade head)"
( cd backend && PYTHONPATH=src uv run alembic upgrade head )

log "Start complete"
