# Architecture

## Strategy

The repo now uses a `Shell + Pipeline` architecture.

- `backend/src/textbook_agent/` is the product shell.
- `backend/src/pipeline/` is the standalone generation engine.
- `frontend/` is the native Lectio client.

Architecture guard: `python tools/agent/check_architecture.py --format text`

## Shell Rules

The shell keeps the DDD-style layering inside `backend/src/textbook_agent/`.

| Layer | May import from | Must NOT import from |
| --- | --- | --- |
| `domain/` | nothing (self-contained) | application, infrastructure, interface |
| `application/` | domain | infrastructure, interface |
| `infrastructure/` | domain | application, interface |
| `interface/` | domain, application, infrastructure | -- |

## Pipeline Rules

- The shell may import the pipeline.
- The pipeline must never import `textbook_agent`.
- The pipeline owns prompts, contract loading, provider registry, graph state, nodes, QC, retries, and Lectio document assembly.
- The shell owns auth, profiles, persistence, HTTP routes, SSE transport, and generation history.
- All live generation flows through `pipeline.run` / `pipeline.api`.

## Runtime Boundaries

- Canonical artifact: structured JSON `PipelineDocument`
- Streaming transport: authenticated SSE at `/api/v1/generations/{id}/events`
- Document hydration: `/api/v1/generations/{id}/document`
- Legacy HTML renderer and iframe viewer are removed from the live architecture

## Current Simulation Status

- The pipeline can generate `simulation` content only when:
  - mode is `balanced` or `strict`
  - the selected template contract advertises `interactionLevel` of `medium` or `high`
  - the selected template includes a `simulation-block` slot
- The Lectio frontend can already render a scaffolded `SimulationBlock`.
- The current public Lectio template registry shipped to this app does not yet expose a `simulation-block`, so simulation cannot appear in normal end-to-end generation yet.
- The next simulation milestone belongs in Lectio first: add a public template with `simulation-block`, render it in the template layout, export contracts again, then validate end-to-end in `Textbook agent`.

## Snapshot References

- `docs/v0.1.0/ARCHITECTURE.md`
