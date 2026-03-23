# Schemas

Current schema source of truth lives in:

- `backend/src/pipeline/api.py`
- `backend/src/pipeline/types/`
- `backend/src/textbook_agent/domain/entities/`
- `backend/src/textbook_agent/application/dtos/`

## Shell Entities

### `Generation`
- `id`
- `user_id`
- `subject`
- `context`
- `mode`: `draft | balanced | strict`
- `status`: `pending | running | completed | failed`
- `document_path`
- `error`
- `error_type`
- `error_code`
- `requested_template_id`
- `resolved_template_id`
- `requested_preset_id`
- `resolved_preset_id`
- `quality_passed`
- `generation_time_seconds`
- `source_generation_id`
- `created_at`
- `completed_at`

### `StudentProfile`
- persistent learner data used by the shell to derive generation inputs
- includes `education_level`, `learning_style`, `preferred_notation`, `preferred_depth`, interests, goals, and learner description

### `User`
- authenticated application identity stored by the shell

## Public Request DTOs

### `GenerationRequest`
- `subject`
- `context`
- `mode`
- `template_id`
- `preset_id`
- optional `section_count`

### `EnhanceGenerationRequest`
- `mode`
- optional `note`

### `GenerationAcceptedResponse`
- `generation_id`
- `status`
- `mode`
- `source_generation_id`
- `events_url`
- `document_url`

## Pipeline Document

### `PipelineDocument`
- `generation_id`
- `subject`
- `context`
- `mode`
- `template_id`
- `preset_id`
- optional `source_generation_id`
- `status`
- ordered `sections: SectionContent[]`
- `qc_reports`
- `quality_passed`
- optional `error`
- `created_at`
- `updated_at`
- optional `completed_at`

`SectionContent` is Lectio-aligned and comes from `backend/src/pipeline/types/section_content.py` plus the matching frontend library in `C:\Projects\lectio`.

### Current Simulation Gate

- `SectionContent` supports an optional `simulation` block.
- The pipeline only attempts to populate it outside `draft` mode.
- A generated `simulation` block is only visible to users when the selected Lectio template actually includes a `simulation-block` component slot.
- The shipped public template set does not currently expose that slot, so simulation remains latent in the runtime for now.

## Stream Event Contract

Closed event union emitted by the pipeline and transported by the shell:

- `pipeline_start`
- `section_started`
- `section_ready`
- `qc_complete`
- `complete`
- `error`

## Viewer Contract

- The public viewer identity is the generation ID.
- The frontend hydrates from `/api/v1/generations/{id}/document`.
- Live progress arrives from `/api/v1/generations/{id}/events`.
- Raw filesystem paths stay internal implementation details.
- HTML artifacts are no longer part of the live viewer contract.
