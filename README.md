# Textbook Generation Agent

An AI-agnostic pipeline that generates complete, personalized textbooks. Users authenticate via Google, create a student profile (education level, interests, learning style, goals), and generate textbooks tailored to who they are and what they need to learn.

## Quick Start

See [docs/v0.1.0/SETUP.md](docs/v0.1.0/SETUP.md) for full setup instructions.

```bash
# Backend
cd backend
uv sync
cp .env.example .env  # fill in API keys + GOOGLE_CLIENT_ID
uv run uvicorn textbook_agent.interface.api.app:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env  # set VITE_GOOGLE_CLIENT_ID
npm run dev
```

Open `http://localhost:5173` → sign in with Google → create profile → generate a textbook.

## Architecture

Python/FastAPI backend with 4-layer DDD (Domain, Application, Infrastructure, Interface) and a SvelteKit frontend. The core is a 6-node pipeline:

```
GenerationContext → Planner → ContentGenerator → DiagramGenerator → CodeGenerator → Assembler → QualityChecker → HTML
```

See [docs/v0.1.0/ARCHITECTURE.md](docs/v0.1.0/ARCHITECTURE.md) for the full breakdown.

## Documentation

- [Original Proposal](docs/PROPOSAL_v1.0.md) — Product specification (with implementation status addendum)
- [Architecture](docs/v0.1.0/ARCHITECTURE.md) — DDD layers, auth flow, pipeline, database
- [Setup Guide](docs/v0.1.0/SETUP.md) — Environment setup and configuration
- [Schemas](docs/v0.1.0/SCHEMAS.md) — All domain entity definitions
- [Development Workflow](docs/v0.1.0/DEVELOPMENT_WORKFLOW.md) — Testing, API endpoints, adding features
- [Changelog](CHANGELOG.md) — Release history
- [Progress Reports](docs/v0.1.0/progress/) — Phase-by-phase handoff documents

## Tests

```bash
cd backend && uv run pytest          # 76 tests
cd backend && uv run ruff check src/ tests/  # Lint
```
