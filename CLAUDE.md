# Textbook Generation Agent - Project Guide

## Project Structure
- `backend/` - FastAPI + Python backend (DDD architecture)
- `frontend/` - SvelteKit + TypeScript frontend
- `docs/` - Versioned project documentation

## Backend
- Package manager: `uv`
- Source layout: `backend/src/textbook_agent/`
- Entry point: `uvicorn textbook_agent.interface.api.app:app`
- CLI: `textbook-agent --profile <path>`
- Tests: `cd backend && uv run pytest`
- Lint: `cd backend && uv run ruff check src/ tests/`

## DDD Layers (dependency flows inward)
- `domain/` - Entities, value objects, pipeline nodes, prompts, ports (abstract). Zero framework imports.
- `application/` - Use cases, orchestrator, DTOs. Depends only on domain.
- `infrastructure/` - LLM providers, storage, renderer, config. Implements domain ports.
- `interface/` - FastAPI routes, CLI. Calls application use cases.

## Key Rules
- Domain layer NEVER imports from other layers
- Every LLM call goes through BaseProvider port (domain/ports/llm_provider.py)
- Every pipeline node validates input/output via Pydantic schemas
- Renderer has NO LLM calls - pure mechanical assembly
- BASE_PEDAGOGICAL_RULES must be injected into every content-generating node
- Schemas are the source of truth - build/verify them first

## Frontend
- Package manager: `npm`
- Framework: SvelteKit with TypeScript
- Dev: `cd frontend && npm run dev`

## Common Commands
```bash
# Backend
cd backend && uv sync                    # Install deps
cd backend && uv run pytest              # Run tests
cd backend && uv run uvicorn textbook_agent.interface.api.app:app --reload  # Dev server

# Frontend
cd frontend && npm install               # Install deps
cd frontend && npm run dev               # Dev server
```
