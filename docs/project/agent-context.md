# Agent Context

This file is the human-readable source of truth for the current project state.

## Current Runtime Shape

- `backend/src/core/` holds shared infrastructure and the shared auth/profile/user layer.
- `backend/src/generation/` is the generation app.
- `backend/src/planning/` is the planning layer used by Teacher Studio.
- `backend/src/pipeline/` is the only live generation engine.
- `backend/src/app.py` is the FastAPI composition entrypoint.
- The canonical saved artifact is a JSON `PipelineDocument`.
- The frontend hydrates from `/document` and appends new sections from `/events`.
- Generation uses a single mode-free path with slot-based model routing.
- `/studio` is the canonical teacher creation flow.

## Current Schema Highlights

- `Generation` stores document metadata, template/preset ids, timing, and failure metadata.
- `PlanningGenerationSpec` stores the reviewed lesson plan that bridges Teacher Studio into generation.
- `GenerationRequest` and `GenerationAcceptedResponse` live under `backend/src/generation/dtos/`.
- `SectionContent` is Lectio-aligned and rendered natively in the frontend.
- `grade_band` is derived in the generation path from `StudentProfile.education_level`.
- `learner_fit` currently defaults to `general`.

## Current Prompt Source of Truth

- Planning prompt/refinement code lives in `backend/src/planning/prompt_builder.py`.
- Media prompt builders live in `backend/src/pipeline/media/prompts/`.
- Non-media pipeline prompt helpers stay under `backend/src/pipeline/`.
- Contract loading lives in `backend/src/pipeline/contracts.py`.
- Reference docs under `docs/` are descriptive only. Code in `backend/src/` is authoritative.

## Current Viewer Contract

- `/textbook/[id]` is generation-centric.
- `/studio` owns teacher intent capture, planning stream, review, and in-studio generation.
- The frontend loads generation detail and saved document by generation ID.
- SSE carries both section-level events and media lifecycle events.
- Viewer state is derived from media-aware section statuses: `planned`, `generating`, `partially_ready`, `blocked_by_required_media`, `ready`, and `failed`.
- Runtime counters are expressed as `media_running` / `media_queued`.
- Raw filesystem paths are internal storage details and are not part of the viewer contract.

## Current Contract Source

- `backend/contracts/` is exported from `C:\Projects\lectio`.
- The current harmonised catalog includes `classification`, `concept-compact`, `diagram-led`, `low-load`, `open-canvas`, `procedure`, `timeline`, `visual-led`, plus the other live-safe templates shipped by Lectio.

## Current Media Runtime

- `backend/src/pipeline/media/planner/media_planner.py` is the single planning authority for section media.
- Static media executes through `backend/src/pipeline/media/executors/diagram_generator.py` and `backend/src/pipeline/media/executors/image_generator.py`.
- Simulation executes through `backend/src/pipeline/media/executors/simulation_generator.py`.
- `process_section` runs `content_generator -> media_planner -> parallel media executors -> section_assembler -> qc_agent`.
- Assembly reads typed `media_frame_results` / `media_slot_results`, not legacy composition-plan assumptions.
- Required media retries are frame-first and report truthfully through media lifecycle events.
- Image provider routing is config-driven via `PIPELINE_IMAGE_PROVIDER` with `gemini`, `openai`, and `xai` support.
