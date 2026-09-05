# Component Lectio Recorded Stabilization Report

## 1. Verdict

`PENDING`

Allowed final verdicts:

- `STABLE FOR SINGLE-WORKER CANARY`
- `STABLE WITH BOUNDED PATCHES`
- `NOT STABLE`

## 2. Final commit and environments

Pending.

## 3. Pre-campaign patches

Pending.

## 4. Run summary and success rate by commit

Pending.

## 5. Latency

Report individual values, median, and range. Do not report p95 for this sample.

## 6. Planner and contract fidelity

Pending.

## 7. Failure, retry, and repair analysis

Pending.

## 8. Database integrity and Builder behavior

Pending.

## 9. Hosted versus local differences

Pending.

## 10. Remaining risks

- DB-backed multi-process lease ownership remains out of scope.

## 11. Legacy recommendation

`PENDING` — choose `NOT YET`, `READY TO FLIP DEFAULT ONLY`, or `READY TO DELETE V3 STUDIO` from evidence. This campaign must not delete V3 Studio.

## 12. Next actions

Pending.

## Campaign gate — PAUSED_P0_UNITS_CUTOVER

- Real-generation count: `0`; CL-LOCAL-001 is not counted as executed.
- P0 blocker: `/units/[id]` preparation redirects to `/studio` (`frontend/src/routes/units/[id]/+page.svelte:322-326`), while the bridge creates the generation and path-preparation initializer omits the `chunked_state_json.control.pipeline` marker (`backend/src/planning/bridge.py:577-648`; `backend/src/generation/path_preparation.py:46-114`). Missing markers resolve to `v3_studio` (`backend/src/generation/pipeline_dispatch.py:70-91`); Studio approval is at `frontend/src/routes/studio/+page.svelte:725`, and the Component Lectio branch requires the persisted marker (`backend/src/generation/v3_studio/router.py:2591-2603`).
- Campaign status: `PAUSED_P0_UNITS_CUTOVER`; no valid Component Lectio campaign generation has run.

## Prior `/studio` pre-generation attempt — INVALID_SCOPE_LEGACY

- The prior attempt is excluded from CL-LOCAL-001 and retained separately as legacy evidence.
- IAB cursor `639`; narrow and propose-intent returned HTTP 200, while signals returned HTTP 500 `text/plain` and the UI reset with `Internal Server Error`.
- The database contains no counted generation row, ordered steps, traces, document, or Builder record, but contains seven paid pre-generation telemetry calls. No manual retry or approval occurred.
- Narrow and propose-intent each succeeded on attempt 2 after one failed attempt. Signal extraction failed on all three attempts at approximately 30 seconds each. Classified `INVALID_SCOPE_LEGACY`; no real-generation count is incremented.
