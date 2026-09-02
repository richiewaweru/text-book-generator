# Phase 00 — Baseline, Inventory and Safety Fence
## Goal
Map the exact local checkout before edits. No product changes.

## Actions
1. Record branch/HEAD/git status/dirty files.
2. Confirm frontend Lectio version and backend contract version.
3. Run contract update/check tooling where safe; report drift.
4. Run baseline backend tests, frontend tests, frontend check and build.
5. Inventory active routes/callers for unit planning, generation start/status/retry, V3 Studio, Builder, PDF, visual regeneration.
6. Inventory every production LLM node/prompt/model/structured output.
7. Inventory resource specs and which are selectable in production UI/API.
8. Inventory background tasks, locks, stale sweep, polling, SSE/events, persistence.
9. Inventory all imports/callers of `generation.v3_studio` and Studio frontend code.
10. Verify reuse inventory.
11. Inventory generation-related DB fields and migrations.
12. Write machine-readable `artifacts/baseline/inventory.json` and human report.

## Gate
GO only when local state, contract relationship, legacy callers, resource entrypoints and baseline failures are known.
