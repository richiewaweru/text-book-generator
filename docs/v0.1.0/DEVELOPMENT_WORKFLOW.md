# Development Workflow - v0.1.0

## Development Environment

### Backend

```bash
cd backend

# Install all dependencies including dev tools
uv sync --all-extras

# Run tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=textbook_agent

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Start dev server
uv run uvicorn textbook_agent.interface.api.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Type check
npx svelte-check --tsconfig ./tsconfig.json

# Build
npm run build
```

## Testing

### Backend Test Structure

```
tests/
├── conftest.py              # Shared fixtures (profile loaders, mock provider)
├── fixtures/                # Learner profile JSON files
│   ├── stem_beginner.json
│   ├── stem_intermediate.json
│   └── stem_advanced.json
├── domain/
│   └── test_entities.py     # Schema validation tests
├── infrastructure/
│   └── test_providers.py    # Provider factory tests
└── interface/
    └── test_api.py          # FastAPI endpoint tests
```

### Running Tests

```bash
cd backend

# All tests
uv run pytest

# Specific test file
uv run pytest tests/domain/test_entities.py

# Specific test class
uv run pytest tests/domain/test_entities.py::TestLearnerProfile

# Verbose output
uv run pytest -v
```

### Test Fixtures

Three learner profiles are provided as test fixtures:

| Fixture | Subject | Age | Depth | Language |
|---|---|---|---|---|
| `stem_beginner.json` | algebra | 14 | survey | plain |
| `stem_intermediate.json` | calculus | 17 | standard | math_notation |
| `stem_advanced.json` | linear algebra | 22 | deep | math_notation |

All three must produce valid output before Phase 1 is complete.

## Code Style

- **Python**: Enforced by `ruff` (line length: 100)
- **TypeScript/Svelte**: Default SvelteKit formatting

## API Endpoints

| Method | Path | Status | Description |
|---|---|---|---|
| GET | `/health` | Implemented | Health check |
| POST | `/api/v1/generate` | Stub (501) | Generate textbook |
| GET | `/api/v1/status/{id}` | Stub (501) | Check generation status |

## DDD Layer Rules

When adding code, respect the dependency direction:

1. **Domain** (`domain/`) - Never import from application, infrastructure, or interface
2. **Application** (`application/`) - May import from domain only
3. **Infrastructure** (`infrastructure/`) - May import from domain (implements ports)
4. **Interface** (`interface/`) - May import from application and domain

If you find yourself importing from a wrong direction, introduce a port (abstract interface) in the domain layer.

## Adding a New Pipeline Node

1. Define input/output schemas in `domain/entities/`
2. Create the node class in `domain/services/` inheriting `PipelineNode[TInput, TOutput]`
3. Add prompt builder in `domain/prompts/`
4. Wire into the orchestrator in `application/orchestrator.py`
5. Add tests in `tests/domain/`

## Build Order (Phase 1 Implementation)

Per the proposal, implement in this order:
1. Schemas first (entities)
2. BaseProvider and provider implementations
3. Pipeline nodes (6 nodes)
4. HTML renderer
5. CLI/API entry points
6. Tests against all 3 fixtures
