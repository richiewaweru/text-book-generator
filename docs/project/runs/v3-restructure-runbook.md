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
- [ ] Not started.

## Sprint 1 Validation Evidence
- Targeted writer tests: `uv run pytest tests/generation/test_v3_generation_writer.py` -> 3 passed, 1 warning.
- Targeted V3 stream tests: `uv run pytest tests/generation/test_v3_studio_generation_stream.py` -> 15 passed, 1 warning.
- Full backend pytest: `uv run pytest` -> 566 passed, 37 failed, 1 warning. Failures are in existing V2/pipeline/PDF tests outside Sprint 1 touched files and are noted as unrelated for this sprint.
- Migration SQL behavior verified against temporary SQLite table.


## Sprint 3 - Extract Shared Contracts
- [ ] Not started.

## Sprint 4 - Delete V2 Pipeline and Planning
- [ ] Not started.

## Sprint 5 - Clean Dependencies and Env Vars
- [ ] Not started.

## Sprint 6 - Clean Frontend V2 Modules
- [ ] Not started.

