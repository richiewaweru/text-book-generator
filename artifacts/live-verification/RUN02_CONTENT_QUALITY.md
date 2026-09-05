# Run 2 Content-Quality Reconciliation (sanitized)

## Scope and disposition

- Generation: `618e4647-dcc9-4b5d-9f8a-5da1b0dda1e6`
- Builder: `b2d595f8-49bc-454e-8c31-973c2e249ad4`
- Verified source SHA: `408eac6` (full SHA is intentionally not repeated here)
- Provider-capacity position: `2 of 12`
- Pipeline: `component_lectio`; requested/resolved preset: `v3-studio` / `v3-studio`; template: `guided-concept-path`
- Classification: `FAIL_P1_CONTENT_QUALITY`
- Campaign treatment: excluded from pass and latency statistics; no Legacy planning was started.

The independent practice block is structurally valid and persisted as `block_ready`, but p2 contains provider self-edit commentary and an incoherent bank-account description. This is a P1 content-quality failure, not a pipeline-selection, lifecycle, or Builder-identity failure.

## Exact persisted independent-practice items

The following strings are copied from the persisted `independent__practice-stack__0` block. Hints are empty for both items; solutions are retained because they are relevant to the content-quality finding.

### p1 — persisted text is coherent

- Stem: `Solve 500 - x = 375 for x, where x is the unknown withdrawal that reduces a $500 balance to $375.`
- Answer: `125`
- Rationale: `Add 375 to both sides to isolate x using the inverse of subtraction.`
- Difficulty: `warm`

The shortened form observed in a UI observation (`...reduces a 375.`) is absent from `generations.document_json`, the independent block checkpoint payload, and `editable_lessons.document_json`. On the available DB evidence, that shortening is rendering-only; it is not a raw persisted p1 corruption.

### p2 — raw persisted corruption

- Stem: `Solve x + 45 = 200 for x, where x is the unknown starting balance before a $45 withdrawal leaves $155? Wait, adjust: actually solve x + 45 = 200 representing balance after adding back or similar withdrawal verification.`
- Answer: `155`
- Rationale: `Subtract 45 from both sides to isolate x using the inverse of addition.`
- Difficulty: `warm`

The `Wait, adjust...` self-edit and the contradictory withdrawal framing are present verbatim in all three persisted surfaces. Therefore this defect is raw provider output carried through assembly and Builder persistence, not a rendering-only defect.

The remaining independent items are persisted as p3 `4x = 240` → `60` and p4 `x / 3 = 50` → `150`, each with an empty hint list and a matching inverse-operation rationale.

## Source, objective, and coverage

- Unit: approved Grade 7 Mathematics, destination objective `By the end, students can solve and check one-step linear equations`.
- Source path lesson: `ce44273a-995b-4583-8d6a-4a1a67dd0b85`, approved path version `25397571-8137-4eca-91c8-1925fe73a0fe` (version 1, revision 4), title/objective `Solve and check one-step linear equations` / `Solve one-step linear equations using inverse operations, then check each solution by substitution.`
- Source planner: `path_planner`; source path lesson revision `2`; path lesson `pack_id` points to this generation.
- Scope contract requires solving `x+a=b`, `x-a=b`, `ax=b`, and `x/a=b` with inverse operations and verifying by substitution; it forbids two-step equations, variables on both sides, inequalities, non-integer fractions/decimals, and systems.
- The canonical plan and selection trace contain five legal, preselected roles: `orient`, `organise`, `guided`, `independent`, and `check`. The independent work order is `wo::independent__practice-stack__0`; its block-ready checkpoint has plan hash `ae1f7c20f7e8040ffe7459e9dcd56396fcf3322650bc9eaba8a4de3fcc1d35b8`, revision `1`, attempt `1`, and no recovery.
- Coverage is substantively present across the four equation forms and the check block, but p2 fails the content-quality gate despite the arithmetic answer being correct.

## Checkpoints, QC, and lifecycle

- Seven ordered `block_ready` checkpoints exist: one each for orient, three organise blocks, guided, independent, and check.
- Independent checkpoint: `2026-09-05 16:04:22.494061`, attempt `1`, recovery absent, work order `wo::independent__practice-stack__0`.
- Guided and check checkpoints completed on attempt `2` with `recovery=repair`; the other five checkpoints completed on attempt `1` with no recovery.
- All seven final checkpoints are `block_ready`; `failed_sections=[]`, `chunked_state.stage=complete`, `chunked_state.control.pipeline=component_lectio`, and generation status is `completed` with no persisted generation error.
- No `v3_trace_runs`/`v3_trace_events` rows or explicit QC report are persisted for this generation. The scalar `quality_passed=true` reflects structural/contract completion and did not catch the semantic p2 contamination; it must not override the P1 content finding.
- Lifecycle (campaign DB timestamps): generation created `2026-09-05 16:02:28.311060`; pipeline selected `16:02:28.483394`; first block ready `16:03:11.879710`; last block ready `16:05:22.169182`; generation completed/heartbeat `16:05:22.455808`; Builder row created/updated `16:05:26.014511`. Derived first-block latency is `43.569s`, total generation latency is `174.145s`, and Builder persistence followed at `177.703s` from generation creation. The stored `generation_time_seconds` is null.

## Provider and transport

- Nine successful execution calls are persisted: four `v3_section_writer` calls on the `standard` lane and five `v3_question_writer` calls on the `fast` lane.
- All nine use `openai_compatible` transport, model `grok-4.3`, endpoint host `api.x.ai`; no failed call or transport retry is persisted.
- Content repairs are represented at the block checkpoint level for guided and check (`2` contract repairs total); the independent block had no retry/repair, allowing p2 contamination to survive.
- Builder linkage is exact: `editable_lessons.source_generation_id` equals the generation ID, `source_type=component_lectio`, and the persisted Builder document contains the same malformed p2 text and `preset_id=blue-classroom`.

## Raw-vs-rendering evidence

The malformed marker `%Wait, adjust%` occurs once in each of `generations.document_json`, the independent `generation_steps.payload`, and `editable_lessons.document_json`. The shortened p1 marker `%reduces a 375%` occurs in none of those surfaces. This establishes raw persisted corruption for p2 and rendering-only status for the shortened p1 observation.

