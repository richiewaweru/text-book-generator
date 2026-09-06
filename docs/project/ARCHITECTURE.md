# Architecture

## Strategy

The live system uses a `Core + Generation + Planning + Telemetry + Pipeline` split.

- `backend/src/core/` owns shared auth, config, database, rate limiting, events, and generic LLM wiring.
- `backend/src/planning/` owns Unit planning, validation, review, and the Component Lectio planning-to-generation bridge.
- `backend/src/generation/` owns generation persistence, orchestration, history/detail routes, SSE transport, and PDF export.
- `backend/src/telemetry/` owns saved reports and LLM usage reporting.
- `backend/src/pipeline/` is the standalone lesson-generation engine and remains the only live content generator.
- `frontend/` is the SvelteKit client. `/units` → Component Lectio → Builder is the only supported lesson-creation workflow; `/studio*` and `/units/legacy*` are retired routes.

Architecture guard: `python tools/agent/check_architecture.py --format text`

## Boundary Rules

- `core/` must not import from `generation/`, `planning/`, `telemetry/`, or `pipeline/`.
- `generation/` may import `core/`, `planning/`, `telemetry/`, and `pipeline/`.
- `planning/` may import `core/` and selected generation bridge types, but must not depend on pipeline LLM internals.
- `telemetry/` may import `core/` and `pipeline.reporting`, but must not import `generation/` or `planning/`.
- `pipeline/` must never import `generation/`, `planning/`, or `telemetry/`.
- The canonical saved artifact is a structured JSON `LessonDocument`, not HTML. Historical pipeline markers and rows remain inert audit data.

## Component Lectio Flow

`/units` owns the supported new-lesson flow. Unit checkpoints dispatch Component Lectio, and successful completion creates or opens the canonical Builder lesson:

1. Teacher creates or resumes a Unit checkpoint.
2. Component Lectio runs through canonical generation APIs and persists checkpoint state.
3. Successful completion creates or opens exactly one Builder `LessonDocument` idempotently.
4. Builder loads and saves the lesson through canonical Builder APIs; packs and PDF render from that document.

Component Lectio produces the canonical `LessonDocument`. It never falls back to Legacy Studio on failure.

## Runtime Boundaries

- Contract catalog: `GET /api/v1/contracts`
- Planning endpoints: `POST /api/v1/brief/resolve-topic`, `/validate`, `/review`, `/plan`, `/commit`
- Generation detail: `GET /api/v1/generations/{id}`
- Document hydration: `GET /api/v1/generations/{id}/document`
- Report hydration: `GET /api/v1/generations/{id}/report`
- Live stream: authenticated SSE at `GET /api/v1/generations/{id}/events`
- PDF export: `POST /api/v1/generations/{id}/export/pdf`

## Retirement contract

- Requests under `/api/v1/v3/*` and `/api/v1/legacy-units/*` return sanitized `410 Gone` responses with code `legacy_pipeline_retired`.
- Removed frontend Legacy routes render a minimal retired-route page with no lesson data or actions.
- Rollback requires redeploying the recorded pre-cutover SHA; there is no automatic runtime fallback.

These legacy endpoints are not live and should stay absent:

- `POST /api/v1/brief`
- `POST /api/v1/brief/stream`
- `POST /api/v1/generations`

## Planning and Contracts

- The route layer in `backend/src/planning/routes.py` is the only place that adapts `PlanningGenerationSpec` into generation inputs.
- Historical planning records may contain `TeacherBrief`-shaped `source_brief` payloads, but they are not a new-lesson entrypoint.
- Lectio contracts under `backend/contracts/` are synced artifacts. App-facing typed payloads come from `pipeline.types.template_contract` and the planning models.

## LLM Routing

- Planning uses `backend/src/planning/llm_config.py`.
- Pipeline routing remains slot-based through the shared `core/llm/` layer.
- Media planning and execution stays under `pipeline.media.*`.

## Snapshot Reference

- Historical architecture notes live under `docs/v0.1.0/`.
