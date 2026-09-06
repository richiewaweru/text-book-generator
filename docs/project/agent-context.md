# Agent Context

This file is the descriptive source of truth for the current live system shape. Code in `backend/src/` and `frontend/src/` remains authoritative.

## Current Runtime Shape

- `backend/src/core/` holds shared auth, config, database, events, and generic LLM utilities.
- `backend/src/planning/` owns Unit planning and the Component Lectio bridge into generation.
- `backend/src/generation/` owns persistence, orchestration, SSE, detail/history APIs, and PDF export.
- `backend/src/telemetry/` owns saved reports and LLM usage reporting.
- `backend/src/pipeline/` is the only live lesson-generation engine.
- `backend/src/app.py` assembles the FastAPI app.
- The canonical saved artifact is a JSON `LessonDocument`; historical pipeline markers remain inert audit data.
- `/units` → Component Lectio → Builder is the only supported new-lesson workflow. `/studio*` and `/units/legacy*` are retired routes.

## Current Schema Highlights

- `TeacherBrief` is the planning input contract.
- `PlanningGenerationSpec` is the reviewed planning artifact that gets committed into generation.
- `GenerationAcceptedResponse` includes startup metadata used by `GenerationView`.
- `Generation.planning_spec_json` stores the committed planning artifact for detail/report hydration.
- `SectionContent` remains Lectio-aligned and renders natively in the frontend viewer.

## Current Component Lectio Flow

- `/units` creates and resumes Unit checkpoints.
- Component Lectio owns generation and persists canonical generation/document state.
- Successful completion creates or opens exactly one Builder lesson idempotently.
- Builder, pack, and PDF surfaces consume canonical `LessonDocument` data.
- `/api/v1/v3/*` and `/api/v1/legacy-units/*` are retired with sanitized `410 Gone` responses (`legacy_pipeline_retired`).
- Rollback is a redeploy of the recorded pre-cutover SHA, never an automatic runtime fallback.

There is no Legacy Studio fallback. Historical rows are retained for audit/rollback only and cannot be selected for execution.

## Prompt and Contract Sources

- Planning prompt entrypoints live in the current planning modules such as `planning/section_composer.py`, `planning/service.py`, and `planning/routes.py`.
- Media prompt builders live under `backend/src/pipeline/media/prompts/`.
- Contract loading lives in `backend/src/pipeline/contracts.py`.
- Synced raw contract JSON lives in `backend/contracts/`; app-facing typed payloads are derived from the current pipeline and planning models.

## Canonical Builder Contract

- The frontend loads generation history through pipeline-neutral APIs and opens canonical Builder lessons.
- Builder loads and saves `LessonDocument` data through Builder CRUD and local recovery.
- Packs and PDF export consume the same canonical document adapter; no V3 API is required.
- Viewer section states are media-aware: `planned`, `generating`, `partially_ready`, `blocked_by_required_media`, `ready`, `failed`, and `unplanned_output`.

## Media Runtime

- `pipeline.media.planner.media_planner` remains the single planning authority for media execution.
- Static media execution lives under `pipeline.media.executors`.
- Required media retries are frame-first and surfaced through runtime events and report state.
