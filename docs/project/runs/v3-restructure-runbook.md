# V3 Restructure Runbook

Objective: Execute `v3-overhaul-sprint-proposals.md` Sprints 1-6 only, in order, with each sprint verified before advancing. Sprint 7 is intentionally skipped.

## Global Rules
- [x] Read `AGENTS.md`, `agents/ENTRY.md`, `agents/project.md`, refactor workflow, and standards.
- [x] Read attached V3 context docs and sprint proposal.
- [x] Execute only numbered proposal tasks.
- [ ] Stop on path discrepancies or ambiguous proposal instructions unless resolved.
- [ ] Run verification checklist and pytest after each sprint.
- [ ] Note unrelated pytest failures and continue only if unrelated to current sprint.

## Sprint 1 - Fix DB Signals
- [x] 1.1 Set `model.mode = "v3"` in both create and update branches of `V3GenerationWriter.upsert_started()`.
- [x] 1.2 Derive `quality_passed` in `write_generation_complete()` from resolved `booklet_status`.
- [x] 1.3 Keep `list_by_user()` compound backward-compatible filter as written in proposal.
- [x] 1.4 Add data-only Alembic migration to backfill `mode = "v3"` for `requested_preset_id = "v3-studio"`.
- [x] 1.5 Update `test_v3_generation_writer.py` assertion from balanced to v3.
- [x] 1.6 Ensure V3 `_upsert_generation_row` calls pass/use `mode="v3"`, preserving explicit legacy compatibility coverage for mode-balanced v3-studio rows.
- [x] Import check: `python -c "import generation.v3_studio.generation_writer"`.
- [x] Verification: `pytest tests/generation/test_v3_generation_writer.py` passes: 3 passed.
- [x] Verification: `pytest tests/generation/test_v3_studio_generation_stream.py` passes: 15 passed.
- [x] Verification: new V3 rows have `mode = "v3"`: ad hoc writer check returned mode v3 and listed true.
- [x] Verification: `list_by_user` returns V3 rows: ad hoc writer check returned mode v3 and listed true.
- [x] Verification: migration backfills existing V3 rows: temp SQLite check changed legacy v3-studio row from balanced to v3 and left V2 row balanced.

## Sprint 2 - Extract Shared Media
- [x] 2.1 Create `backend/src/media/` with `__init__.py`.
- [x] 2.2 Create `backend/src/media/providers/` and copy provider files. Also copied `image_client.py` because copied providers import it directly.
- [x] 2.3 Create `backend/src/media/providers/registry.py` with `IMAGE_*` primary env vars and `PIPELINE_IMAGE_*` fallback.
- [x] 2.4 Create `backend/src/media/storage/` and copy `image_store.py` plus `__init__.py`.
- [x] 2.5 Update `v3_execution/executors/visual_executor.py` imports to `media.*`.
- [x] 2.6 Reviewed `generation/image_pipeline_health.py`; it does not import `pipeline.media`, only V2 `pipeline.providers`/`pipeline.storage`, so it is marked for Sprint 4 deletion/restructure.
- [x] 2.7 Add new `IMAGE_*` vars to `backend/.env.example` alongside existing `PIPELINE_IMAGE_*` vars.
- [x] 2.8 Add `backend/tests/media/test_providers_registry.py` with `media.providers.registry` imports and primary/fallback env coverage.
- [x] Verification: `pytest tests/media/test_providers_registry.py` passes: 10 passed.
- [x] Verification: fake V3 visual execution emitted `visual_generation_started` then `visual_ready` with an image URL.
- [x] Verification: `from media.providers.registry import get_image_client` works.
- [x] Verification: no remaining `from pipeline.media` in `backend/src/v3_execution/`.

## Sprint 2 Validation Evidence
- Media registry tests: `uv run pytest tests/media/test_providers_registry.py` -> 10 passed.
- V3 execution tests: `uv run pytest tests/v3_execution` -> 37 passed, 1 warning.
- Import check: `uv run python -c "from media.providers.registry import get_image_client, load_image_provider_spec; import media.storage.image_store; import v3_execution.executors.visual_executor"` -> passed.
- V3 visual path check: fake provider/store execution emitted `visual_generation_started` and `visual_ready` and returned `https://cdn.example/gen-visual-check/section-1/visual-1.png`.
- Full backend pytest: `uv run pytest` -> 576 passed, 37 failed, 1 warning. Failures match existing V2/pipeline/PDF areas outside Sprint 2 touched files and are noted as unrelated for this sprint.

## Sprint 1 Validation Evidence
- Targeted writer tests: `uv run pytest tests/generation/test_v3_generation_writer.py` -> 3 passed, 1 warning.
- Targeted V3 stream tests: `uv run pytest tests/generation/test_v3_studio_generation_stream.py` -> 15 passed, 1 warning.
- Full backend pytest: `uv run pytest` -> 566 passed, 37 failed, 1 warning. Failures are in existing V2/pipeline/PDF tests outside Sprint 1 touched files and are noted as unrelated for this sprint.
- Migration SQL behavior verified against temporary SQLite table.


## Sprint 3 - Extract Shared Contracts
- [x] 3.1 Create `backend/src/contracts/` with `__init__.py`.
- [x] 3.2 Copy `pipeline/contracts.py` to `contracts/lectio.py` and update internal imports.
- [x] 3.3 Copy `pipeline/types/generation_manifest.py` to `contracts/generation_manifest.py`.
- [x] 3.4 Copy `pipeline/types/template_contract.py` to `contracts/template_contract.py`.
- [x] 3.5 Copy `pipeline/types/section_content.py` to `contracts/section_content.py` for V3 validation imports.
- [x] 3.6 Update V3 imports from `pipeline.contracts` and `pipeline.types` to `contracts.*`.
- [x] 3.7 Move `pipeline/block_generate.py` to `generation/block_generate.py`; copied direct prompt dependency to `generation/block_generate_prompts.py` and rewired to `contracts.*` plus V3 model slots so Sprint 4 pipeline deletion will not break block generation.
- [x] 3.8 Update `generation/routes.py` block-generate import to `generation.block_generate`.
- [x] 3.9 Replace `pipeline/contracts.py` with a re-export shim to `contracts.lectio`.
- [x] Verification: `pytest tests/v3_execution tests/v3_blueprint tests/routes/test_blocks_generate.py` passes: 47 passed.
- [x] Verification: block-generate endpoint tests pass.
- [x] Verification: no `from pipeline.contracts import` remains in V3 scoped source/tests.
- [x] Verification: `from contracts.lectio import get_contract` works.

## Sprint 3 Validation Evidence
- Targeted tests: `uv run pytest tests/v3_execution tests/v3_blueprint tests/routes/test_blocks_generate.py` -> 47 passed, 2 warnings.
- Import check: `uv run python -c "import generation.block_generate; import generation.block_generate_prompts; import generation.routes; from contracts.lectio import get_contract; import pipeline.contracts; import v3_execution.runtime.lectio_validation"` -> passed.
- V3 scoped grep: no `from pipeline.contracts import`, `pipeline.types`, or `from pipeline.types` hits in `backend/src/v3_execution`, `backend/src/v3_blueprint`, `backend/src/generation/v3_studio`, `backend/tests/v3_execution`, or `backend/tests/v3_blueprint`.
- Full backend pytest: `uv run pytest` -> 575 passed, 38 failed, 2 warnings. The additional V3 ordering failure passed in isolation and appears to be full-suite shared DB/order pollution; the rest are existing V2/pipeline/PDF failures.

## Sprint 4 - Delete V2 Pipeline and Planning
- [ ] Not started.

## Sprint 5 - Clean Dependencies and Env Vars
- [ ] Not started.

## Sprint 6 - Clean Frontend V2 Modules
- [ ] Not started.



