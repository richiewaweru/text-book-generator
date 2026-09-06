# Textbook Generation Agent - Project Guide

## Project Structure
- `backend/` - FastAPI + Python backend
- `frontend/` - SvelteKit + TypeScript frontend
- `docs/project/` - live project docs
- `docs/v0.1.0/` - archival snapshot docs

## Backend
- Package manager: `uv`
- Shared core source root: `backend/src/core/`
- Generation app source root: `backend/src/generation/`
- Planning source root: `backend/src/planning/`
- Pipeline source root: `backend/src/pipeline/`
- Entry point: `uvicorn app:app`
- Validation: `python tools/agent/validate_repo.py --scope all`
- Architecture guard: `python tools/agent/check_architecture.py --format text`

## Key Runtime Contracts
- The core owns auth primitives, shared database access, and generic infrastructure.
- The generation app owns auth-aware HTTP, persistence, generation orchestration, and SSE transport.
- The planning app owns Unit planning and the Component Lectio bridge into generation.
- The pipeline owns prompts, contract loading, providers, graph orchestration, QC, and Lectio document assembly.
- The canonical saved artifact is a JSON `LessonDocument`; historical pipeline rows remain inert audit data.
- `/units` → Component Lectio → Builder is the only supported new-lesson workflow.
- `GET /api/v1/contracts` and the canonical Units, generation-history, Builder, pack-document, and PDF endpoints are the live workflow APIs.
- `/studio*` and `/units/legacy*` are retired frontend routes. `/api/v1/v3/*` and `/api/v1/legacy-units/*` return sanitized `410 Gone` responses with code `legacy_pipeline_retired`.
- Rollback is an operational redeploy of the recorded pre-cutover SHA; runtime fallback to Legacy Studio is not supported.
- Public lesson viewing is document-centric: Builder, active pack views, and PDF export consume the canonical `LessonDocument` produced by Component Lectio.
- The pipeline must never import `generation` or `planning`.

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

## Contract Sync
- Sync contracts and generated Python types from the installed frontend `lectio` package via `uv run python tools/update_lectio_contracts.py`.
- The Textbook repo should treat the synced Lectio JSON contracts and generated adapter as the planning/template source of truth.
