# Architecture

## Strategy

DDD 4-layer architecture in `backend/src/textbook_agent/`. Full rules are in `agents/project.md`.

Architecture guard: `python tools/agent/check_architecture.py --format text`

## Layer Rules

| Layer | May import from | Must NOT import from |
| --- | --- | --- |
| `domain/` | nothing (self-contained) | application, infrastructure, interface |
| `application/` | domain | infrastructure, interface |
| `infrastructure/` | domain | application, interface |
| `interface/` | domain, application, infrastructure | -- |

## Key Design Decisions

- **Domain is pure**: zero framework imports. Entities, value objects, pipeline nodes, ports (abstract interfaces).
- **Dependency inversion**: infrastructure implements domain ports (e.g., `BaseProvider` in `domain/ports/llm_provider.py`).
- **Interface is thin**: FastAPI routes call application use cases. No business logic in routes.
- **Renderer has no LLM calls**: pure mechanical assembly of content into HTML.

## Snapshot References

- `docs/v0.1.0/ARCHITECTURE.md`
