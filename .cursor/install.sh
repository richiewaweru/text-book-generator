#!/usr/bin/env bash
# Idempotent repository bootstrap for the Textbook Generation Agent Cloud Agent
# environment. Runs after the source tree is checked out. Installs system
# packages, language toolchains, and project dependencies. Safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '\n[install] %s\n' "$*"; }

# --- uv (Python package manager) --------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  log "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

# --- PostgreSQL (the Alembic migrations require Postgres, not SQLite) --------
if ! ls /usr/lib/postgresql >/dev/null 2>&1; then
  log "Installing PostgreSQL"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib
fi

# --- Backend Python dependencies --------------------------------------------
log "Syncing backend dependencies (uv sync --all-extras)"
( cd backend && uv sync --all-extras )

# --- Playwright Chromium (used by PDF export + health readiness) ------------
log "Installing Playwright Chromium"
( cd backend && sudo -E env "PATH=$PATH" uv run playwright install --with-deps chromium )

# --- Frontend dependencies --------------------------------------------------
log "Installing frontend dependencies (npm ci)"
( cd frontend && npm ci )

# --- Local env files (gitignored; created only if missing) ------------------
# Google OAuth client id may be provided as any of these secret names.
GOOGLE_CLIENT_ID_RESOLVED="${GOOGLE_CLIENT_ID:-${PUBLIC_GOOGLE_CLIENT_ID:-${VITE_GOOGLE_CLIENT_ID:-}}}"

if [ ! -f backend/.env ]; then
  log "Creating backend/.env"
  # Reuse an injected JWT secret if present; otherwise generate one.
  JWT_SECRET="${JWT_SECRET_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}"
  cat > backend/.env <<EOF
APP_ENV=development

DATABASE_URL=postgresql+asyncpg://textbook:textbook@localhost:5432/textbook_agent
DB_ECHO=false
RUN_MIGRATIONS_ON_STARTUP=true
JSON_LOGS=false
LOG_LEVEL=INFO

LECTIO_CONTRACTS_DIR=./contracts
DEFAULT_PAGINATION_LIMIT=20

GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID_RESOLVED}
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080

FRONTEND_ORIGIN=http://localhost:5173
LESSON_BUILDER_PUBLIC_URL=http://localhost:5173

PDF_EXPORT_ENABLED=true
PDF_RENDER_BASE_URL=http://localhost:5173
PDF_TEMP_DIR=outputs/pdf

REPORT_OUTPUT_DIR=outputs/reports
EOF
fi

if [ ! -f frontend/.env ]; then
  log "Creating frontend/.env"
  # The browser build only sees PUBLIC_*/VITE_* vars, so map the resolved id in.
  cat > frontend/.env <<EOF
PUBLIC_API_URL=http://localhost:8000
PUBLIC_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID_RESOLVED}
VITE_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID_RESOLVED}
EOF
fi

log "Install complete"
