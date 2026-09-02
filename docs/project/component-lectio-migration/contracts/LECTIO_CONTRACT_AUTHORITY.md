# Lectio Contract Authority

## Source of truth
Use exported Lectio contracts; do not duplicate its registry.

Authoritative app artifacts:
- `backend/contracts/lectio-content-contract.json`
- `backend/contracts/section-content-schema.json`
- `backend/contracts/component-field-map.json`
- generated Python contract models under `backend/src/contracts/`

Existing boundary: `backend/src/contracts/lectio.py`.

Reuse helpers such as `get_component_card`, `get_component_schema_shape`, `get_planner_index`, `get_template_contract`, `get_formatting_policy` and field/schema helpers.

## Planner-facing vocabulary
Use the current Lectio `planner_index`; never invent page primitives. At the researched 0.6.0 baseline it includes:
`section-header`, `hook-hero`, `explanation-block`, `prerequisite-strip`, `what-next-bridge`, `interview-anchor`, `callout-block`, `summary-block`, `section-divider`, `definition-card`, `definition-family`, `glossary-rail`, `insight-strip`, `key-fact`, `comparison-grid`, `worked-example-card`, `process-steps`, `practice-stack`, `quiz-check`, `reflection-prompt`, `student-textbox`, `short-answer`, `fill-in-blank`, `pitfall-alert`, `diagram-block`, `diagram-compare`, `diagram-series`, `timeline-block`, `simulation-block`, `answer-key`.

Full registry entries that are inline/manual-only/not available to the active template must not leak into AI candidate sets.

## Forbidden abstraction leak
Do not introduce component IDs like `prose`, `table`, `aside`, `figure`, `generic-card`, `page-block`.

## Document authority
`LessonDocument` is the portable generator/editor contract. Preserve:
- flat blocks keyed by stable IDs;
- `DocumentSection.block_ids` as within-section document order;
- each block's `component_id`, `content`, `position`;
- exact component payload validation.

## Version gate
Phase 00 must assert installed frontend Lectio version, backend contract version, and local source version where available. Reconcile drift before proceeding.
