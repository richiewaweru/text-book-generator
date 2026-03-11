# Setup Guide - v0.1.0

## Prerequisites

- **Python** 3.11+ ([python.org](https://python.org))
- **uv** (Python package manager) - Install: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Node.js** 20+ ([nodejs.org](https://nodejs.org))
- **npm** (comes with Node.js)
- **Git**

## Backend Setup

```bash
cd backend

# Install all dependencies (creates .venv automatically)
uv sync --all-extras

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your API keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...

# Verify installation
uv run pytest
```

### Running the Backend

```bash
cd backend

# Development server with auto-reload
uv run uvicorn textbook_agent.interface.api.app:app --reload

# Verify health check
curl http://localhost:8000/health
# Should return: {"status":"ok","version":"0.1.0"}
```

### CLI Usage (Phase 1 - skeleton only)

```bash
cd backend
uv run textbook-agent --profile tests/fixtures/stem_beginner.json
```

## Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment config
cp .env.example .env

# Start development server
npm run dev
```

The frontend dev server starts at `http://localhost:5173` and proxies API requests to the backend at `http://localhost:8000`.

## Running Both Together

Open two terminals:

```bash
# Terminal 1 - Backend
cd backend && uv run uvicorn textbook_agent.interface.api.app:app --reload

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## Environment Variables

### Backend (`.env`)

| Variable | Default | Description |
|---|---|---|
| `PROVIDER` | `claude` | LLM provider: `claude` or `openai` |
| `ANTHROPIC_API_KEY` | | Anthropic API key |
| `OPENAI_API_KEY` | | OpenAI API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model ID |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model ID |
| `MAX_RETRIES` | `2` | Max retry attempts per pipeline node |
| `QUALITY_CHECK_ENABLED` | `true` | Enable quality checker node |
| `TEMPERATURE` | `0.3` | LLM temperature |
| `OUTPUT_DIR` | `outputs/` | Generated textbook output directory |
| `OUTPUT_FORMAT` | `html` | Output format |

### Frontend (`.env`)

| Variable | Default | Description |
|---|---|---|
| `PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

## Project Structure

```
Textbook agent/
├── backend/          # FastAPI + Python (DDD architecture)
│   ├── src/textbook_agent/
│   │   ├── domain/          # Core business logic
│   │   ├── application/     # Use cases, orchestration
│   │   ├── infrastructure/  # Providers, storage, renderer
│   │   └── interface/       # FastAPI routes, CLI
│   └── tests/
├── frontend/         # SvelteKit + TypeScript
│   └── src/
└── docs/             # Project documentation
```
