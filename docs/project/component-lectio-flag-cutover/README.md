# Casa Handoff — Component Lectio Default-Path Flag

## Goal

Make the new **Component Lectio** path the default generation path behind a runtime feature flag, while preserving the current V3 Studio path as an explicit rollback option.

This is **not** the legacy-deletion phase and **not** the Codex live E2E verification phase.

```text
Casa implementation
    ↓
inspect implementation
    ↓
Codex live end-to-end verification
    ↓
patch bounded defects
    ↓
prove stability
    ↓
delete legacy Studio path
```

## Read order

1. `CASA_MASTER_PROMPT.md`
2. `CURRENT_BRANCH_FINDINGS.md`
3. `IMPLEMENTATION_CONTRACT.md`
4. `FILE_IMPACT_MANIFEST.md`
5. `ACCEPTANCE_TESTS.md`
6. `POST_IMPLEMENTATION_REPORT_TEMPLATE.md`

## Non-negotiables

- Default flag value selects `component_lectio`.
- Legacy remains available as an explicit rollback.
- No automatic runtime fallback from Component Lectio to V3 Studio after an error.
- The selected pipeline is persisted per generation.
- Retry/status/resume follows the generation's persisted pipeline, not a later environment flag.
- Every generation exposes enough metadata/logging to prove which pipeline actually handled it.
- Do not delete V3 Studio yet.
- Do not perform the Codex browser/live verification in this task.
