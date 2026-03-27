# Schemas

Current schema source of truth lives in:

- `backend/src/planning/models.py`
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

### `StudioBriefRequest`
- `intent`
- `audience`
- `prior_knowledge`
- `extra_context`
- `signals.topic_type`
- `signals.learning_outcome`
- `signals.class_style[]`
- `signals.format`
- `preferences.tone`
- `preferences.reading_level`
- `preferences.explanation_style`
- `preferences.example_style`
- `preferences.brevity`
- `constraints.more_practice`
- `constraints.keep_short`
- `constraints.use_visuals`
- `constraints.print_first`

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

### `PlanningGenerationSpec`
- `id`
- `template_id`
- `preset_id`
- `template_decision`
- `lesson_rationale`
- `directives`
- `committed_budgets`
- ordered `sections`
- optional `warning`
- `source_brief_id`
- `source_brief`
- `status`: `draft | reviewed | committed`

### `StudioTemplateContract`
- exported JSON contract served by `GET /api/v1/contracts`
- includes `available_components`, `component_budget`, `max_per_section`, `section_role_defaults`, and `signal_affinity`
- current harmonised catalog ids:
  - `classification`
  - `compare-and-apply`
  - `concept-compact`
  - `diagram-led`
  - `formal-track`
  - `guided-concept-path`
  - `guided-discovery`
  - `interactive-lab`
  - `low-load`
  - `open-canvas`
  - `procedure`
  - `timeline`
  - `visual-led`

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

Planning stream events emitted by `POST /api/v1/brief/stream`:

- `template_selected`
- `section_planned`
- `plan_complete`
- `plan_error`

## Viewer Contract

- The public viewer identity is the generation ID.
- The frontend hydrates from `/api/v1/generations/{id}/document`.
- Live progress arrives from `/api/v1/generations/{id}/events`.
- Teacher lesson creation now lives at `/studio` with the state flow `idle -> planning -> reviewing -> generating`.
- `POST /api/v1/brief` remains available only as a deprecated compatibility shim.
- Raw filesystem paths stay internal implementation details.
- HTML artifacts are no longer part of the live viewer contract.
