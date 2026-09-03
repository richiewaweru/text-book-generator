# COMPONENT LECTIO PATCH REPORT

## 1. Verdict

```text
READY FOR CONTROLLED LIVE CODEX RUN
```

Flag cutover, semantic selection, stable `block_id` join, lane dispatch, canonical Lectio `LessonDocument` validation, and block-scoped retry are implemented and covered by targeted tests. DB-backed multi-process leases remain a known P1 and are **not** claimed fixed. A controlled single-worker Codex live run is appropriate; multi-worker production is not.

## 2. Changes

### Semantic selector
- **Before:** `run_component_lectio_execution` discarded `signals`/`resource_spec` and used `heuristic_select_components`.
- **After:** Production default is `run_lectio_semantic_selector` (LLM + one validation repair, no heuristic fallback). Lesson context (subject, grade, topic, outcome) is passed into selector payload. Heuristic remains for tests, mocked pipeline, and Studio rollback.
- **Files:** [`backend/src/v3_blueprint/planning/component_selector.py`](backend/src/v3_blueprint/planning/component_selector.py), [`backend/src/v3_blueprint/planning/canonical_plan.py`](backend/src/v3_blueprint/planning/canonical_plan.py), [`backend/src/generation/component_lectio/service.py`](backend/src/generation/component_lectio/service.py)
- **Also:** `writer_excluded` visuals (e.g. `diagram-block`) stay in candidate sets so the selector can choose visual-lane work; manual-only media (`image-block`, `video-embed`) stay excluded.
- **Tests:** S1–S5 in `tests/generation/test_component_lectio_prelive.py`

### Stable block identity
- **Before:** `orders_by_component[component_id]` collapsed duplicate slugs.
- **After:** Join hierarchy `block_id` → `work_order_id` → scoped `section_id + component_id`. Content executor UUIDs are stamped to canonical `block_id`.
- **Files:** [`backend/src/generation/component_lectio/lane_dispatch.py`](backend/src/generation/component_lectio/lane_dispatch.py)
- **Tests:** I1–I3

### Lane dispatch
- **Before:** `include_visual=False`; items/answer_key funneled through `execute_section`.
- **After:** `include_visual=True`. content → `execute_section` (one ExactWorkOrder); items → `execute_questions`; visual → `execute_visual`; answer_key → `execute_answer_key` after item results. `execute_items` (card diagnostics) is not used.
- **Files:** `lane_dispatch.py`, `service.py`
- **Tests:** L1, L2, L5, integration

### Canonical LessonDocument
- **Before:** `{schema, title, plan_*, sections, blocks, partial}`
- **After:** Lectio 0.6.0 fields (`version`, `id`, `title`, `subject`, `preset_id`, `source`, `source_generation_id`, `sections` with `template_id`/`position`, `blocks`, `media`, timestamps). `plan_hash` / `pipeline` / `partial` live in chunked `control_meta`. Validate then persist.
- **Files:** [`backend/src/v3_execution/runtime/lesson_document.py`](backend/src/v3_execution/runtime/lesson_document.py), [`backend/src/contracts/lesson_document.py`](backend/src/contracts/lesson_document.py), [`frontend/src/lib/builder/adapters/from-generation.ts`](frontend/src/lib/builder/adapters/from-generation.ts)
- **Tests:** D1, D3, frontend adapter tests including malformed `template_id`

### Block-scoped retry
- **Before:** Retry re-ran a whole section writer batch.
- **After:** Per ExactWorkOrder / `block_id` with structured errors; ready siblings skipped; exhaustion → `assembly_blocked`, not complete.
- **Files:** `service.py`
- **Tests:** R1–R4, phase 8 injection

## 3. Architecture trace

Deterministic integration fixture (`test_phase7_architecture_integration`) using forced legal picks:

```text
IntentPlan (components=[])
→ candidate sets per role (resource spec ∩ template − forbidden − manual-only)
→ selector choices:
   orient: hook-hero, diagram-block
   build:  definition-card, explanation-block
   model:  worked-example-card, diagram-block
   practice: practice-stack
   close:  summary-block, quiz-check
→ CanonicalExecutionPlan block_ids e.g.
   orient__hook-hero__0
   orient__diagram-block__1
   build__definition-card__0
   build__explanation-block__1
   model__worked-example-card__0
   model__diagram-block__1
   practice__practice-stack__0
   close__summary-block__0
   close__quiz-check__1
→ ExactWorkOrders lanes: content / visual / items
→ executors: execute_section / execute_visual / execute_questions
→ generation_steps block_ready by block_id
→ validate_lesson_document → Builder generationToBuilderDocument(pipeline=component_lectio)
```

## 4. Duplicate-component proof

`diagram-block` in **orient** and **model**:

- Distinct block IDs: `orient__diagram-block__1` vs `model__diagram-block__1`
- I2: persist only orient diagram ready → resume invokes visual executor only for the model diagram

## 5. Retry proof

R1 (`test_r1_one_invalid_block_retries_only_that_block`):

```text
hook-hero execution count        = 1
definition-card execution count  = 1
explanation-block execution count = 2   (first lectio validation failure, then repair)
```

## 6. Document-contract proof

Method: [`validate_lesson_document`](backend/src/contracts/lesson_document.py) required-field contract derived from Lectio 0.6.0 Builder import (`version===1`, `id/title/subject/preset_id/source/sections/blocks/media`, section `template_id`). Frontend additionally calls `validateDocument` from `lectio` after structural checks. D1 assembled document: `errors == []`. Generation fields (`plan_hash`, `pipeline`) must not appear on the portable document.

## 7. No-fallback proof

Existing `test_gate4_no_automatic_legacy_fallback_on_lectio_failure` still passes: Lectio failure records `assembly_blocked` with persisted `component_lectio`; `_run_chunked_stage2_pipeline` call count is 0. Unrecoverable injection test keeps `resolve_generation_pipeline == component_lectio`.

## 8. Test results

| Command | Result | Notes |
|---|---|---|
| `uv run pytest tests/generation/test_pipeline_flag_cutover.py tests/generation/test_component_lectio_prelive.py tests/generation/test_component_lectio_e2e.py tests/v3_blueprint tests/v3_execution tests/resource_specs -q` | PASS | 238 passed |
| `npm test -- src/lib/builder/adapters/from-generation.test.ts` | PASS | 9 passed |
| `npm run check` | PASS | pre-existing unused CSS warnings on `units/[id]/+page.svelte` |
| `npm run build` | PASS | Vite production build succeeded (unused CSS warnings only) |
| `python tools/agent/check_architecture.py --format text` | PASS | no violations |
| Full `tests/generation` in one process | FAIL (contaminated) | sqlite `database is locked` on shared test DB; also pre-existing `router.resume_stage2` AttributeError in `test_v3_chunked_lifecycle.py` — not introduced by this patch |

## 9. Remaining known risks

```text
P1 — lease/ownership: not DB-backed (in-process LeaseStore / task map). Do not run multi-worker production until Phase 07.
P2 — answer_key lane only fires when an answer-key component is selected; items still couple expected answers into execute_answer_key when present.
P2 — live LLM selector quality is unproven until Codex four-subject run (tests use injected selectors).
```

## 10. Recommendation

The branch is **ready for the controlled Codex browser/Vercel four-subject run** on a **single worker**. Do not treat distributed lease durability as solved. Studio remains as explicit `GENERATION_PIPELINE_DEFAULT=v3_studio` rollback.
