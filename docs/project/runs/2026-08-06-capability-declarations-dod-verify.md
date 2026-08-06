# Capability declarations — DoD verification

**Branch:** `xplore`  
**Date:** 2026-08-06  
**Related commit:** `d4c2d46` (Replace prerequisite string matching with capability declarations)

## Checklist

- [x] Legacy-backfill behavioral test added (`test_backfilled_legacy_unit_aligned_labels_approve_unaffected`)
- [x] Planning regression suite green (52 tests)
- [x] Grep: no `allowed_external`, no fuzzy/similarity/embed prerequisite matching in `backend/src/planning`
- [x] Live unit snapshot queried (Railway DB)

## Test evidence

```text
pytest backend/tests/planning/test_path_service.py \
       backend/tests/planning/test_path_contracts.py \
       backend/tests/planning/test_path_routes.py -q
# 52 passed
```

New test: `test_backfilled_legacy_unit_aligned_labels_approve_unaffected` — intake labels exact-match planner `external_prerequisites` → zero unconfirmed rows → `approve_path` succeeds without replan.

Existing regression: `test_planner_reword_surfaces_unconfirmed_declaration` — inverse invariant (`approve_path` blocked labels == `open_assumptions` claimed labels).

## Live unit snapshot

**Unit:** `3ce6c13c-3a40-4473-859a-260feb82a0dc`  
**Path version:** `5709a178-f0cc-4055-83a1-8b9b53a53af3`  
**Alembic head:** `20260806_0032`

| Field | Value |
|---|---|
| `unit.status` | `approved` |
| `path_version.status` | `approved` |
| `reaches_destination` | `true` |
| `prerequisite_risks` | `[]` |
| Unconfirmed declarations | **0** |

All five declaration rows are `source=teacher_intake`, `confirmed=true`. `starting_knowledge` contains the planner labels (`multiply fractions`, `understand fraction concept`, `divide whole numbers`) — consistent with both assumptions having been resolved as **known** and the path locked in without replan.

**Interpretation:** The live failure case is already resolved in production DB. Post-migration backfill confirmed intake rows; the two reworded planner labels were confirmed via resolve-before-approve (or equivalent), matching the intended fix behavior.

## Manual re-verify (if resetting a draft)

1. Ensure Alembic includes `20260806_0032`.
2. Open `/units/3ce6c13c-3a40-4473-859a-260feb82a0dc` with a draft path whose planner emits reworded externals.
3. Expect two confirm rows: `multiply fractions`, `understand fraction concept`.
4. Answer both **Yes** → panel empty → lock-in succeeds without replan.

For a clean-room repro without touching production data, use `test_planner_reword_surfaces_unconfirmed_declaration`.

## Prohibitions verified

- No `allowed_external` construction in planning package
- No fuzzy / embedding / similarity reconciliation of prerequisites
- `unit.starting_knowledge` retained (still written on `known` resolve)
