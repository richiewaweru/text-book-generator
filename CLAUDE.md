# Textbook Generation Agent - Project Guide

## Project Structure
- `backend/` - FastAPI + Python backend
- `frontend/` - SvelteKit + TypeScript frontend
- `docs/project/` - live project docs
- `docs/v0.1.0/` - archival snapshot docs

## Backend
- Package manager: `uv`
- Source root: `backend/src/textbook_agent/`
- Entry point: `uvicorn textbook_agent.interface.api.app:app`
- Validation: `python tools/agent/validate_repo.py --scope all`
- Architecture guard: `python tools/agent/check_architecture.py --format text`

## Key Runtime Contracts
- Domain remains framework-free and owns entities, prompts, ports, and pipeline nodes.
- All LLM calls flow through `BaseProvider`.
- The renderer is mechanical only and produces the standalone textbook HTML artifact.
- Public textbook viewing is generation-centric: `/textbook/[id]` maps to a generation ID, and the frontend fetches HTML through the authenticated generation-owned backend route.
- The current `SectionContent` schema has 11 fields, including `prerequisites_block`, `practice_problems`, `interview_anchor`, and `think_prompt`.
- Shared prompt rules live in `backend/src/textbook_agent/domain/prompts/` and are versioned through the composed prompt bundle.

## Frontend
- Package manager: `npm`
- Dev: `cd frontend && npm run dev`
- Auth: Google OAuth via Google Identity Services
- Viewer: authenticated iframe rendering of the standalone textbook HTML

## Live Docs
- `docs/project/agent-context.md`
- `docs/project/ARCHITECTURE.md`
- `docs/project/SETUP.md`
- `docs/project/DEVELOPMENT_WORKFLOW.md`
- `docs/project/SCHEMAS.md`
