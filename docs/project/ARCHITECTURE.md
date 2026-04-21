# Architecture

## Strategy

The repo now uses a `Core + Generation + Planning + Pipeline` architecture.

- `backend/src/core/` holds shared infrastructure: config, auth, database, error handling, shared events, and generic LLM helpers.
- `backend/src/generation/` owns generation persistence, orchestration, and SSE transport.
- `backend/src/planning/` owns Teacher Studio planning.
- `backend/src/pipeline/` is the standalone generation engine.
- `backend/src/app.py` assembles the FastAPI application.
- `frontend/` is the native Lectio client and can also be served statically from Docker.

Architecture guard: `python tools/agent/check_architecture.py --format text`

## Boundary Rules

- `core/` must not import from `generation`, `planning`, or `pipeline`.
- `generation/` may import `core`, `planning`, and `pipeline`.
- `planning/` may import `core` and the generation bridge, but must not import pipeline LLM internals.
- `pipeline/` must never import `generation` or `planning`.
- The pipeline owns prompts, contract loading, provider registry, graph state, nodes, QC, retries, and Lectio document assembly.
- The generation app owns auth, profiles, persistence, HTTP routes, Teacher Studio planning, SSE transport, and generation history.
- All live generation flows through `pipeline.run` / `pipeline.api`.

## Planning Rules

- `backend/src/planning/` normalizes teacher intent, scores templates, composes sections, routes visuals, and performs the single planning refinement call.
- Planning emits `PlanningGenerationSpec` artifacts for review. It does not generate lesson content.
- Routes under `planning/routes.py` are the only place that should adapt planning outputs into generation requests.
- The Lectio contracts in `backend/contracts/` are synced from `frontend/node_modules/lectio/contracts/` via `tools/update_lectio_contracts.py`.

## Runtime Boundaries

- Canonical artifact: structured JSON `PipelineDocument`
- Canonical teacher creation route: `/studio`
- Planning catalog endpoint: `GET /api/v1/contracts`
- Planning stream endpoint: `POST /api/v1/brief/stream`
- Planning commit-and-start endpoint: `POST /api/v1/brief/commit`
- Legacy compatibility path: `POST /api/v1/brief` (deprecated shim)
- Streaming transport: authenticated SSE at `/api/v1/generations/{id}/events`
- Document hydration: `/api/v1/generations/{id}/document`
- Legacy HTML renderer and iframe viewer are removed from the live architecture
- Section media planning is owned by `pipeline.media.planner.media_planner`
- Static and simulation execution live under `pipeline.media.executors`
- Media retries are frame-first and surfaced through media lifecycle SSE events

## Current LLM Routing

- Model routing is slot-based and mode-free.
- Pipeline LLM helpers resolve concrete models through the shared `core/llm/` layer.
- Planning uses its own planning-specific LLM config instead of borrowing pipeline defaults.

## Snapshot References

- `docs/v0.1.0/ARCHITECTURE.md`
