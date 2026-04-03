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
- Prompt builders live in `backend/src/pipeline/prompts/`.
- Contract loading lives in `backend/src/pipeline/contracts.py`.
- Reference docs under `docs/` are descriptive only. Code in `backend/src/` is authoritative.

## Current Viewer Contract

- `/textbook/[id]` is generation-centric.
- `/studio` owns teacher intent capture, planning stream, review, and in-studio generation.
- The frontend loads generation detail and saved document by generation ID.
- SSE carries pipeline progress and section updates.
- Raw filesystem paths are internal storage details and are not part of the viewer contract.

## Current Contract Source

- `backend/contracts/` is exported from `C:\Projects\lectio`.
- The current harmonised catalog includes `classification`, `concept-compact`, `diagram-led`, `low-load`, `open-canvas`, `procedure`, `timeline`, `visual-led`, plus the other live-safe templates shipped by Lectio.

## Image Generation (raster path)

- Sections where `visual_policy.mode == "image"` generate a PNG via Gemini instead of an SVG spec.
- **New node:** `backend/src/pipeline/nodes/image_generator.py` runs in Phase 3 parallel alongside `diagram_generator`. The two nodes are mutually exclusive by their own gates.
- **GCS storage:** `backend/src/core/storage/gcs_image_store.py` — uploads to `GCS_BUCKET_NAME` (currently `lectio-bucket-1`) and returns a signed URL (1-hour TTL). When `GCS_BUCKET_NAME` is unset the node silently no-ops, so local dev works without credentials.
- **Gemini client:** `backend/src/pipeline/providers/gemini_image_client.py` uses `gemini-3.1-flash-image-preview` via `generate_content_stream()` (multimodal text+image response). Factory: `get_gemini_image_client()` (LRU-cached, reads `GOOGLE_CLOUD_NANO_API_KEY`).
- **Type changes:** `DiagramPlan.mode: Literal["svg", "image"] | None` (composition.py). `DiagramContent.image_url` was already present.
- **Wiring:** `composition_planner` reads `plan.visual_policy.mode` and stamps it onto `DiagramPlan.mode`. `diagram_generator` has an early-exit gate for `mode == "image"`.
- **Required env vars:** `GCS_BUCKET_NAME`, `GCS_SERVICE_ACCOUNT_JSON`, `GCS_IMAGE_BASE_URL` (optional), `GOOGLE_CLOUD_NANO_API_KEY`.
- **Lectio frontend** (`image_url` branch in the diagram block component) is deferred — to be done in the Lectio repo.
