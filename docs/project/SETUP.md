# Setup

## Install

| Surface | Directory | Command |
| --- | --- | --- |
| Backend (Python) | `backend/` | `uv sync --all-extras` |
| Frontend (SvelteKit) | `frontend/` | `npm ci` |

## Project-Local Tools

Validation and architecture scripts live in `tools/agent/`:

```bash
python tools/agent/validate_repo.py --scope all          # Run all validation
python tools/agent/validate_repo.py --scope backend       # Backend only
python tools/agent/check_architecture.py --format text    # Check layer boundaries
```

## Dev Servers

```bash
cd backend && uv run uvicorn textbook_agent.interface.api.app:app --reload
cd frontend && npm run dev
```

## Snapshot References

- `docs/v0.1.0/SETUP.md`
