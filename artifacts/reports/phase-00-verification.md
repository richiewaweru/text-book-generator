# Phase 00 Verification Report

## Identity
- branch: `xplore`
- baseline HEAD: `27a114bc85717481673ee6dad875a603d58bebb9`
- ending HEAD: `67b695f` (`docs(migration): Phase 00 Component Lectio baseline inventory`)
- dirty files preserved:
  - `RESTRUCTURE_PROGRESS.md` (docs note only)
  - `backend/src/core/config.py` (CRLF/whitespace noise)
  - `backend/src/v3_execution/config/__init__.py` (CRLF/whitespace noise)
  - `backend/src/v3_execution/prompts/item_prompt.py` (unrelated TYPE_CHECKING stub)

## Scope implemented
Phase 00 only: map local checkout, confirm Lectio contract authority, inventory routes/LLM/specs/persistence/Studio callers, run baseline suites, write machine-readable inventory + this report. **No product/runtime behavior changes.**

Also vendored the migration pack into `docs/project/component-lectio-migration/` so later phases do not depend on the Downloads zip.

## Files changed
- none of production code

## Files created
- `docs/project/component-lectio-migration/**` (living contract pack)
- `artifacts/baseline/inventory.json`
- `artifacts/baseline/backend-pytest.txt`
- `artifacts/baseline/frontend-vitest.txt`
- `artifacts/baseline/frontend-check.txt`
- `artifacts/baseline/frontend-build.txt`
- `artifacts/reports/phase-00-verification.md`

## Files deleted
- none

## Reuse decisions
Verified all pack-listed reuse targets exist and remain the starting points for later phases:
- `backend/resources/specs/lesson.yaml` (`orient → build → model → practice → close`)
- `backend/src/resource_specs/schema.py`
- `backend/resources/component-selector-v1.txt`
- `backend/src/contracts/lectio.py`
- `backend/src/v3_blueprint/planning/section_expander.py`
- `backend/src/v3_execution/runtime/lectio_validation.py`
- `backend/src/v3_blueprint/planning/persistence.py`
- Builder `from-generation.ts` + `generation-stream.ts`

## Prompt changes
- none

## Contract/schema changes
- none. `tools/update_lectio_contracts.py` ran; frontend installed Lectio `0.6.0` matches backend contract `"version": "0.6.0"`; sync produced **no git drift**.

## API changes
- none

## DB/migration changes
- none. Inventory notes: `GenerationModel.chunked_state_json` + `last_heartbeat`; append-only `GenerationStepModel`; **no lease columns** (Phase 07).

## Tests added
- none (inventory/report only)

## Commands/results

| Command | Result |
|---|---|
| `uv run python tools/update_lectio_contracts.py` | synced; no drift |
| `cd backend && uv run pytest -q --tb=no` | **574 passed**, 1 warning; exit 0 |
| `cd frontend && npm test` | **319 passed**, **1 failed** (timeout); exit 1 |
| `cd frontend && npm run check` | **0 errors**, 2 unused-CSS warnings; exit 0 |
| `cd frontend && npm run build` | **built OK** (adapter-vercel); exit 0 |

### Known baseline failure (recorded, not fixed in Phase 00)
- `frontend/src/routes/lessons/page.test.ts` — `renders all four groups, class labels, and row actions` timed out at 5000ms.
- Classification: pre-existing / flaky timeout; does not block knowing local state.

## Failure-injection results
- N/A (Phase 00)

## Remaining legacy dependencies
- V3 Studio router mounted at `/api/v1/v3` from `generation/routes.py`
- In-memory `v3_studio_store` ownership/queues
- In-process `_background_tasks`, `_chunked_stage2_tasks`, visual/snapshot locks
- `V3GenerationWriter.fail_stale_running()` on app lifespan
- Production callers of `generation.v3_studio`: app, routes, path_preparation, compile_orders, question_writer prompts, structural planning retry/expander/persistence, shadow
- Frontend `/studio` routes + `frontend/src/lib/api/v3.ts` + V3 pack→Builder adapter path
- All **seven** resource specs still primary-selectable in Studio `RESOURCE_TYPES`

## Deviations
- Local HEAD is ahead of any researched GitHub snapshot in the pack (expected; pack says Phase 00 must record local truth).
- Reshape wave already landed `GenerationStepModel` + lanes; Phase 06/07 build on that rather than inventing from scratch.
- No DB worker lease yet.

## Unexpected findings
- Frontend Vitest has one timeout failure on `/lessons` page test under full-suite load; suites otherwise green.
- Contract sync tooling is write-in-place but currently idempotent against installed `lectio@0.6.0`.

## GO / NO-GO

**GO**

Local branch/HEAD/dirty state, Lectio 0.6.0 alignment, Studio/legacy callers, resource entrypoints, runtime topology, LLM nodes, and baseline failures are known. Phase 01 may begin.

Do not start Phase 01 product edits in the same commit as this report.
