# Full Legacy Studio Cutover Checklist

**Branch:** `xplore`
**Pre-cutover SHA:** `e0e867e3e8e7d567923c7a6e9d95af729f16f617`
**Protected file:** `artifacts/reports/COMPONENT_LECTIO_PATCH_REPORT.md` — never stage or overwrite

## Units replacement

- [x] Validate preparation serialization and automatic Builder creation (focused regressions)
- [ ] Repair Run 5 linkage without another provider generation
- [ ] Verify Units → Builder, terminal state, diagram serving, and warning metadata

## Consumer cutover

- [x] Make `/units` the only new-lesson entrypoint
- [x] Move dashboard/history to canonical generation APIs
- [x] Move Builder status and recovery away from Studio
- [x] Move active packs and PDF to canonical `LessonDocument`
- [x] Remove Legacy navigation and mutable/readable frontend surfaces

## Backend retirement

- [x] Replace V3 startup recovery with pipeline-neutral recovery
- [x] Retire `/api/v1/v3/*` and `/api/v1/legacy-units/*` with sanitized HTTP 410
- [x] Remove V3 Studio router, writer, session store, and execution-only helpers
- [x] Require `component_lectio` for all active generation
- [x] Preserve historical markers and rows as inert data

## Validation

- [ ] Focused backend and frontend tests
- [x] Component Lectio final-contract, pre-live, cutover, and E2E suites — 81 passed, 1 known warning
- [x] Full backend pytest in isolated temporary directory — 613 passed, 1 known warning
- [ ] Frontend check and build
- [x] Architecture validation — no violations
- [ ] PostgreSQL migration and restart/recovery verification
- [x] Static source zero-caller audit — no active V3 imports or HTTP callers
- [ ] Post-cutover local browser scenarios
- [ ] Exact-SHA hosted canaries

## Evidence

- [x] Record logical commits and validation results
- [x] Record last Legacy-capable rollback SHA — `e0e867e3e8e7d567923c7a6e9d95af729f16f617`
- [ ] Commit evidence separately from implementation

## Current blockers

- Docker Desktop cannot start because the zero-byte runtime reparse point `C:\Users\richi\AppData\Local\Docker\run\dockerInference` cannot be removed by Docker. The PostgreSQL volume was not reset or modified. Manual recovery is to fully quit Docker Desktop, delete only that exact runtime entry, and relaunch Docker Desktop; do not use factory reset.
- Until PostgreSQL is available, Run 5 linkage repair, exact-SHA runtime/browser proof, PostgreSQL restart recovery, fresh local scenarios, and hosted canaries remain pending. Provider calls remain paused.
- The final committed frontend has a passing canonical dashboard test (`4 passed`) and root-route test (`3 passed`); the final aggregate/check/build rerun remains incomplete because frontend tooling repeatedly stalled on this Windows host. Earlier pre-history check/build passed and is not claimed as final-SHA proof.
