# Setup

## Install

| Surface | Directory | Command |
| --- | --- | --- |
| Backend (Python) | `backend/` | `uv sync --all-extras` |
| Frontend (SvelteKit) | `frontend/` | `npm ci` |

The frontend consumes the local Lectio package from `C:\Projects\lectio`, so that sibling repo must exist on disk for native development and Docker builds.

## Docker Stack

Use the repository-root compose file for the full stack:

```bash
cp .env.example .env
docker compose up --build
```

For database-only Docker development, keep the app processes native and run:

```bash
docker compose --profile dev up db-dev
```

## Local Auth and Env Requirements

- Backend provider keys must be present in `backend/.env`.
- `frontend/.env` must define `VITE_GOOGLE_CLIENT_ID`.
- `backend/.env` must define `GOOGLE_CLIENT_ID`.
- The Google Cloud OAuth client must list both `http://localhost:5173` and `http://127.0.0.1:5173` under `Authorized JavaScript origins`.
- If the Google OAuth consent screen is still in Testing mode, the local sign-in email must also be added as a test user.

## Contract Sync

Refresh exported Lectio contracts into the backend consumer directory:

```bash
cd "C:\Projects\lectio"
npm run export-contracts -- --out "C:\Projects\Textbook agent\backend\contracts\lectio"
```

Run the export again whenever Lectio template contracts change.

## Project-Local Tools

Validation and architecture scripts live in `tools/agent/`:

```bash
python tools/agent/validate_repo.py --scope all          # Run all validation
python tools/agent/validate_repo.py --scope backend       # Backend only
python tools/agent/check_architecture.py --format text    # Check shell + pipeline boundaries
cd frontend && npm run test                               # Frontend helper tests
```

## Dev Servers

```bash
cd backend && uv run uvicorn app:app --reload
cd frontend && npm run dev -- --host=127.0.0.1 --port=5173
```

For Google sign-in demos, prefer opening `http://localhost:5173`.

## Snapshot References

- `docs/v0.1.0/SETUP.md`
