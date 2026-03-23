# Project Config

AI-powered shell + pipeline system that generates personalized Lectio-native textbooks from learner profiles.
Monorepo: `backend/` (FastAPI + Python) and `frontend/` (SvelteKit + TypeScript).

## Architecture Rules

The backend uses a `Shell + Pipeline` architecture:

- `backend/src/textbook_agent/` is the product shell.
- `backend/src/pipeline/` is the standalone generation engine.

The shell keeps the DDD 4-layer structure:

| Layer | May import from | Must NOT import from |
| --- | --- | --- |
| `domain/` | nothing | application, infrastructure, interface |
| `application/` | domain | infrastructure, interface |
| `infrastructure/` | domain | application, interface |
| `interface/` | domain, application, infrastructure | -- |

Critical invariants:
- Domain has zero framework imports -- pure entities, value objects, and ports
- The shell may import `pipeline`; `pipeline` must never import `textbook_agent`
- All live generation goes through the pipeline engine
- The canonical artifact is a structured JSON document, not HTML

## Validation Commands

See `CLAUDE.md` for the full command reference. Quick alternative:

```bash
python tools/agent/validate_repo.py --scope all       # Runs everything
python tools/agent/check_architecture.py --format text # Shell + pipeline boundary check
```

## Conventions

- **Commits**: `type(scope): summary` -- types: feat, fix, refactor, docs, test, chore, ci, build
- **Branches**: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`
- **Protected branches**: `main`
- **Package managers**: `uv` (backend), `npm` (frontend)

## Key Entities

- `StudentProfile` -- persistent learner data (age, education, interests, goals). Stored in DB.
- `Generation` -- stored generation metadata plus document, lineage, and failure state.
- `GenerationRequest` -- per-request DTO (subject, context, mode, template_id, preset_id, optional section_count).
- `PipelineDocument` -- canonical saved output used by the frontend viewer and enhancement flow.
