# Textbook Generation Agent

A standalone, AI-agnostic pipeline that accepts a learner profile and produces a complete, personalized, high-quality textbook. The system generates a document shaped by who is learning, what they already know, and how deeply they need to go.

## Quick Start

See [docs/v0.1.0/SETUP.md](docs/v0.1.0/SETUP.md) for full setup instructions.

```bash
# Backend
cd backend
uv sync
cp .env.example .env  # fill in API keys
uv run uvicorn textbook_agent.interface.api.app:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Architecture

See [docs/v0.1.0/ARCHITECTURE.md](docs/v0.1.0/ARCHITECTURE.md) for the full DDD architecture breakdown.

## Documentation

- [Original Proposal](docs/PROPOSAL_v1.0.md) - Product proposal and specification
- [Architecture](docs/v0.1.0/ARCHITECTURE.md) - System design and DDD layers
- [Setup Guide](docs/v0.1.0/SETUP.md) - Development environment setup
- [Schemas](docs/v0.1.0/SCHEMAS.md) - All domain entity definitions
- [Development Workflow](docs/v0.1.0/DEVELOPMENT_WORKFLOW.md) - How to develop, test, contribute
- [Engineering Docs](docs/engineering/README.md) - Current workflow, governance, and release process
- [Automation Assets](automation/README.md) - Reusable scripts, templates, and review-agent prompts
- [Changelog](CHANGELOG.md) - Release ledger and milestone notes
