# Textbook Generation Agent

AI-powered core + generation + planning + pipeline system for generating personalized Lectio-native textbooks from learner context.

## Quick Start

Use the live project docs in [`docs/project/`](docs/project/README.md). The versioned `docs/v0.1.0/` set is archival.

```bash
# Full stack with Docker
cp .env.example .env
docker compose up --build

# Native backend
cd backend
uv sync --all-extras
cp .env.example .env
uv run uvicorn app:app --reload

# Native frontend
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Optional contract refresh from the sibling Lectio repo:

```bash
cd "C:\Projects\lectio"
npm run export-contracts -- --out "C:\Projects\Textbook agent\backend\contracts\lectio"
```

Open `http://localhost:5173`, sign in, create a profile, and generate a lesson.

## Runtime Policy Configuration

The generation runtime is now configured through env-backed settings instead of hard-coded policy constants. The main knobs are:

- `GENERATION_MAX_CONCURRENT_PER_USER`
- `PIPELINE_CONCURRENCY_<MODE>_<RESOURCE>_MAX`
- `PIPELINE_TIMEOUT_<NAME>_SECONDS`
- `PIPELINE_TIMEOUT_GENERATION_{BASE,PER_SECTION,CAP}_SECONDS`
- `PIPELINE_RERENDER_<MODE>_SECTION_MAX`
- `PIPELINE_RETRY_<NAME>_MAX_ATTEMPTS`

`backend/.env.example` is the authoritative local reference. For Docker, copy the same variables into the repo-root `.env` so `docker-compose.yml` can pass them through to the backend container.

## Local Run Requirements

- Provider API keys must be present in `backend/.env`.
- Runtime policy knobs live in `backend/.env`; for Docker runs, mirror the same names in the repo-root `.env`.
- Google OAuth must be configured for local development:
  - `frontend/.env` needs `VITE_GOOGLE_CLIENT_ID`
  - `backend/.env` needs `GOOGLE_CLIENT_ID`
  - the Google Cloud OAuth client must allow `http://localhost:5173` and `http://127.0.0.1:5173` as authorized JavaScript origins
  - if the OAuth consent screen is still in Testing mode, your sign-in email must be added as a test user
- The sibling `C:\Projects\lectio` repo must exist locally because the frontend consumes it as a file dependency.
- If Lectio template contracts change, refresh the backend copies with:

```bash
cd "C:\Projects\lectio"
npm run export-contracts -- --out "C:\Projects\Textbook agent\backend\contracts\lectio"
```

## Current Architecture

- Shared infrastructure in `backend/src/core/`
- Generation app in `backend/src/generation/`
- Planning in `backend/src/planning/`
- Generation engine in `backend/src/pipeline/`
- FastAPI composition entrypoint in `backend/src/app.py`
- SvelteKit frontend in `frontend/` with native Lectio rendering
- JSON document persistence plus authenticated SSE streaming
- Slot-based model routing and a single generation path

## Live Docs

- [`docs/project/README.md`](docs/project/README.md)
- [`docs/project/ARCHITECTURE.md`](docs/project/ARCHITECTURE.md)
- [`docs/project/SETUP.md`](docs/project/SETUP.md)
- [`docs/project/DEVELOPMENT_WORKFLOW.md`](docs/project/DEVELOPMENT_WORKFLOW.md)
- [`docs/project/SCHEMAS.md`](docs/project/SCHEMAS.md)
- [`docs/project/runs/`](docs/project/runs/)

## Validation

```bash
python tools/agent/validate_repo.py --scope all
python tools/agent/check_architecture.py --format text
```
