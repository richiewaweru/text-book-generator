# Project Config

AI-powered pipeline that generates personalized HTML textbooks from learner profiles.
Monorepo: `backend/` (FastAPI + Python) and `frontend/` (SvelteKit + TypeScript).

## Architecture Rules

Backend follows DDD 4-layer architecture in `backend/src/textbook_agent/`:

| Layer | May import from | Must NOT import from |
| --- | --- | --- |
| `domain/` | nothing | application, infrastructure, interface |
| `application/` | domain | infrastructure, interface |
| `infrastructure/` | domain | application, interface |
| `interface/` | domain, application, infrastructure | -- |

Critical invariants:
- Domain has zero framework imports -- pure entities, value objects, and ports
- Every LLM call goes through the `BaseProvider` port (`domain/ports/llm_provider.py`)
- Renderer has no LLM calls -- pure mechanical assembly

## Validation Commands

See `CLAUDE.md` for the full command reference. Quick alternative:

```bash
python tools/agent/validate_repo.py --scope all       # Runs everything
python tools/agent/check_architecture.py --format text # Layer boundary check
```

## Conventions

- **Commits**: `type(scope): summary` -- types: feat, fix, refactor, docs, test, chore, ci, build
- **Branches**: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`
- **Protected branches**: `main`
- **Package managers**: `uv` (backend), `npm` (frontend)

## Key Entities

- `StudentProfile` -- persistent learner data (age, education, interests, goals). Stored in DB.
- `GenerationContext` -- ephemeral per-generation context built from profile + request. Never stored.
- `GenerationRequest` -- per-request DTO (subject, optional depth/language overrides).
- `BaseProvider` -- abstract LLM port. All providers implement this interface.
