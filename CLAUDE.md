# Textbook Generation Agent - Project Guide

## Project Structure
- `backend/` - FastAPI + Python backend
- `frontend/` - SvelteKit + TypeScript frontend
- `docs/project/` - live project docs
- `docs/v0.1.0/` - archival snapshot docs

## Backend
- Package manager: `uv`
- Shell source root: `backend/src/textbook_agent/`
- Pipeline source root: `backend/src/pipeline/`
- Entry point: `uvicorn textbook_agent.interface.api.app:app`
- Validation: `python tools/agent/validate_repo.py --scope all`
- Architecture guard: `python tools/agent/check_architecture.py --format text`

## Key Runtime Contracts
- The shell owns auth, profiles, persistence, HTTP routes, and SSE transport.
- The pipeline owns prompts, contract loading, providers, graph orchestration, QC, and Lectio document assembly.
- The canonical saved artifact is a JSON `PipelineDocument`.
- Public textbook viewing is generation-centric: `/textbook/[id]` maps to a generation ID, hydrates from `/document`, and streams updates from `/events`.
- The pipeline must never import `textbook_agent`.

## Frontend
- Package manager: `npm`
- Dev: `cd frontend && npm run dev`
- Auth: Google OAuth via Google Identity Services
- Viewer: native Lectio rendering of streamed section content

## Live Docs
- `docs/project/agent-context.md`
- `docs/project/ARCHITECTURE.md`
- `docs/project/SETUP.md`
- `docs/project/DEVELOPMENT_WORKFLOW.md`
- `docs/project/SCHEMAS.md`
