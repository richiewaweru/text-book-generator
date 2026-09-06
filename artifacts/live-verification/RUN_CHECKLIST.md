# Component Lectio Recorded Stabilization Checklist

**Branch:** `xplore`  
**Starting SHA:** `8509233`  
**Campaign owner:** Sol  
**Execution rule:** one backend worker and one active generation at a time

## Pre-live fixes

- [x] Reject failed, omitted, or source-less visual outputs before `block_ready`
- [x] Preserve usable `flagged_quality` warnings outside portable Lectio content
- [x] Align reflection guidance with the `transfer` enum
- [x] Synchronize Component Lectio scalar and chunked terminal state
- [x] Make repeated checkpoint events append-only and deterministic
- [x] Persist selector and attempt evidence
- [x] Run focused backend regression suites
- [x] Run frontend check and build
- [x] Run architecture and full repository validation
- [x] Record pre-live commits and approved campaign SHA

## Run 4 visual-QC correction

- [x] Record Run 4 `FAIL_P1_VISUAL_QC` on exact SHA `b41a6d1`; exclude from pass and latency statistics
- [x] Record corrective commits `04a2412`, `9e1dba8`, and `c3a2632`
- [x] Record user-directed temporary policy: QC unavailable → retain usable visual as `flagged_quality`; explicit reject and missing media/source still block
- [x] Run affected-suite validation on `c3a2632`: `86 passed, 1 known warning`
- [x] Record PostgreSQL 16 `0033 → 0032 → 0033` migration roundtrip; current Run 4 DB head observed as `0034`
- [ ] Prove post-`c3a2632` exact-SHA restart, readiness/image probe, and replacement generation before resuming the campaign

## Local campaign

## Units cutover workstream

- [ ] A — atomically persist the selected pipeline on Units preparation and dispatch review/approve/progress/retry from the persisted marker
- [ ] B — expose the idempotent Builder-native open service for Units generations
- [ ] C — validate the end-to-end Units → Component Lectio → Builder path on one worker with zero Studio fallback

- [x] Record sanitized local environment and readiness evidence (fix SHA health endpoints passed; prior authorized image probe passed)

- [x] Verify first-load Units hydration fix on `738dde4a8c0596b6cb29f6c14fd8996974b7dd98`; no paid lesson runs
- [x] Final aggregate gate on `738dde4a8c0596b6cb29f6c14fd8996974b7dd98` exited `0` (Ruff/backend/frontend/tooling pass; isolated temp cleaned)
- [x] Campaign gate — `PAUSED_P0_UNITS_CUTOVER`; real-generation count `0`; unit-to-Studio/pipeline-marker scope blocker recorded
- [ ] CL-LOCAL-001 — Grade 7 Math — not run; paused before valid Component Lectio scope
- [x] L01 Units → Builder reconciliation — `INVALID_SCOPE_SELECTION`; provider-capacity generation `1 of 12` on old SHA `63390e64`; selected lesson 0 explicitly excluded solving and content did not match the campaign scenario; Builder linkage/UI interaction passed, `default` preset warning confirmed/fixed separately; no L02 started; excluded from latency/pass statistics
- [x] Run 2 independent-practice reconciliation — `FAIL_P1_CONTENT_QUALITY`; provider-capacity generation `2 of 12` on SHA `408eac6`; p2 raw persisted provider self-edit/contradictory stem; shortened p1 observation absent from persisted surfaces and rendering-only on available evidence; 9 successful xAI calls, 2 block repairs, complete terminal state/Builder linkage; excluded from pass/latency statistics; no Legacy planning started
- [x] Run 3 corrected Grade 7 Math reconciliation — `PASS`; generation `7623d9cc` on SHA `9871fcaa`; eight successful DeepSeek text calls, no visual calls, complete terminal state/Builder linkage; browser verified blue-classroom, four equation forms/substitution, no residue, currency preserved; duplicate awaiting-review row `303e332e` orphaned with zero provider calls
- [ ] CL-LOCAL-002 — Grade 5 Science with visual
- [ ] CL-LOCAL-003 — Grade 8 Social Studies
- [ ] CL-LOCAL-004 — Grade 8 English; edit/save/reload
- [ ] CL-LOCAL-005 — Grade 6 Math variation
- [ ] CL-LOCAL-006 — Grade 4 Science visual variation; PDF
- [ ] CL-LOCAL-007 — Industrial urbanization variation
- [ ] CL-LOCAL-008 — unfamiliar metaphor variation
- [ ] Confirm four consecutive PASS/PASS_WITH_RECOVERY runs on one SHA (run 3 is the first passing local run after run 2's P1)

## Hosted canary

- [ ] Prove exact approved SHA in Vercel and Railway canary deployments
- [ ] Prove `component_lectio`, one Railway replica, and one Uvicorn worker
- [ ] Prove hosted health, image readiness, logs, DB access, and migration head
- [ ] CL-HOSTED-001 — Math
- [ ] CL-HOSTED-002 — Science with visual; PDF
- [ ] CL-HOSTED-003 — Social Studies
- [ ] CL-HOSTED-004 — English; edit/save/reload

## Closeout

- [ ] Reconcile browser, network, logs, DB, and document evidence for every run
- [ ] Calculate medians and ranges without p95
- [ ] Publish final verdict and legacy recommendation
- [ ] Commit sanitized campaign evidence without the unrelated patch report

## P0 pre-campaign blocker

- `/units/[id]` “Make the lesson” redirects to `/studio`: `frontend/src/routes/units/[id]/+page.svelte:322-326`.
- The bridge creates a generation and path preparation omits `chunked_state_json.control.pipeline`: `backend/src/planning/bridge.py:577-648`; `backend/src/generation/path_preparation.py:46-114`; missing markers resolve to `v3_studio`: `backend/src/generation/pipeline_dispatch.py:70-91`.
- Studio owns generation approval: `frontend/src/routes/studio/+page.svelte:725`; Component Lectio execution is selected only from the persisted marker: `backend/src/generation/v3_studio/router.py:2591-2603`.
- Prior `/studio` attempt is `INVALID_SCOPE_LEGACY`, retained separately with seven paid pre-generation calls; it is not CL-LOCAL-001 and does not increment the real-generation count.

## Validation Evidence

Record commands, exit codes, counts, warnings, and approved SHA in `PATCH_LOG.md`.
