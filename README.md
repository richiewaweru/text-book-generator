# Textbook Generation Agent

AI-powered pipeline for generating personalized HTML textbooks from learner context.

## Quick Start

Use the live project docs in [`docs/project/`](docs/project/README.md). The versioned `docs/v0.1.0/` set is archival.

```bash
# Backend
cd backend
uv sync --all-extras
cp .env.example .env
uv run uvicorn textbook_agent.interface.api.app:app --reload

# Frontend
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`, sign in, create a profile, and generate a textbook.

## Current Architecture

- FastAPI backend with 4-layer DDD in `backend/src/textbook_agent/`
- SvelteKit frontend in `frontend/`
- Six pipeline nodes plus a final HTML renderer stage
- Rulebook-based textbook output rendered as a standalone HTML document
- Frontend viewer loads authenticated textbook HTML by generation ID and mounts it with `iframe srcdoc`

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
