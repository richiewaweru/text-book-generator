# Component Lectio Runtime Migration — Read Me First

## Goal
Restructure `richiewaweru/text-book-generator` branch `xplore` so the production path is lesson-first, component-oriented, durable, Builder-native, and smaller. This is not a new Lectio schema. The existing Lectio component model and `LessonDocument` remain authoritative.

## Repositories
- Application: `richiewaweru/text-book-generator`, branch `xplore`.
- Contract authority: `richiewaweru/lectio`, branch `master`.
- Researched baseline: Lectio `0.6.0`; frontend pins `lectio: 0.6.0`; backend exported `lectio-content-contract.json` is the same 0.6.0 contract.

## Decisions already made
1. Lesson is the primary authored teaching resource.
2. Use one general lesson spec in this round; subject-specific specs are deferred.
3. Lesson spec narrows pedagogy before component selection.
4. Component selector never reasons over the full Lectio catalogue when a role-specific candidate set can be supplied.
5. Use Lectio metadata (`cognitive_job`, capabilities, section field, capacity, template constraints) instead of duplicating metadata.
6. Exact Lectio component contracts are loaded only after selection.
7. Final generated artifact is a valid Lectio `LessonDocument` that opens directly in Builder.
8. Preserve Builder, Builder block generation, visual regeneration, polling, streaming, existing executors, immutable generation steps, and exact Lectio validation.
9. Remove V3 Studio orchestration only after every useful responsibility has a tested replacement.
10. DeepSeek/API strict-tool schema enforcement is deferred. Keep current structured-output + validation behavior in this migration.
11. Do not redesign the database unless a phase proves a minimal additive migration is necessary.

## Existing code that already matches the direction
- `backend/resources/specs/lesson.yaml` already defines `orient -> build -> model -> practice -> close` and role-specific preferred/allowed/forbidden components.
- `backend/src/resource_specs/schema.py` already models role component constraints and allowed/forbidden helpers.
- `backend/resources/component-selector-v1.txt` already selects only from `allowed_components`, uses `cognitive_job`, respects budgets and minimizes components.
- `backend/src/contracts/lectio.py` already loads Lectio component cards, schema shapes, planner index, template constraints and formatting policy.
- `backend/src/v3_blueprint/planning/section_expander.py` already loads selected component cards only.
- `backend/src/v3_execution/runtime/lectio_validation.py` already validates field payloads and full `SectionContent` using generated Pydantic contracts.
- `backend/src/v3_blueprint/planning/persistence.py` already uses immutable `GenerationStepModel` rows for concurrent progress.
- Frontend polling and Builder streaming/merge concepts already exist.

The migration should promote, connect, simplify and harden these pieces rather than create parallel replacements.

## Order
Run `phases/PHASE_00...PHASE_10` in order. Each phase must write a verification report and may not hand off to the next phase until GO.
