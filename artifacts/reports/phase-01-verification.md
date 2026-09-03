# Phase 01 Verification Report

## Identity
- branch: `xplore`
- baseline HEAD: `0830a7fbd522bf41448bf82e62b19ca2bae0cfd8` (pre-Phase-01 working tree)
- ending HEAD: working tree (uncommitted Phase 01 changes)
- dirty files preserved:
  - `RESTRUCTURE_PROGRESS.md`
  - `backend/src/generation/v3_studio/router.py` (brief-into-lanes)
  - `backend/src/v3_execution/runtime/lanes.py`
  - `backend/src/v3_execution/runtime/stage2_lanes.py`
  - `backend/tests/v3_execution/test_lanes.py`
  - `backend/tests/v3_execution/test_stage2_lanes.py`
  - `backend/.env` / `frontend/.env` (local secrets; not part of this phase)

## Scope implemented
Phase 01 only: promote `lesson.yaml` as production primary grammar; add deterministic Lectio-legal candidate intersection; keep other resource YAMLs; no Stage 1 / selector / Studio changes.

## Files changed
- `backend/resources/specs/lesson.yaml` — version `1.1`; production-primary header; arc unchanged (`orient → build → model → practice → close`); narrow preferred/allowed/forbidden retained; no Lectio field/schema duplication added
- `backend/src/resource_specs/schema.py` — document raw vs legal helpers; add `required_roles()`
- `backend/src/resource_specs/loader.py` — `PRIMARY_RESOURCE_TYPE = "lesson"`, `get_primary_spec()`, registry asserts primary present
- `backend/src/resource_specs/__init__.py` — export primary + candidate APIs

## Files created
- `backend/src/resource_specs/candidates.py` — deterministic intersection helper
- `backend/tests/resource_specs/test_candidates.py`
- `artifacts/reports/phase-01-verification.md`

## Files deleted
- none

## Reuse decisions
- Extended existing `resource_specs` package rather than a parallel spec framework
- Reused `get_planner_index`, `get_template_contract`, `get_component_card`, `MANUAL_ONLY_COMPONENT_IDS` from `contracts/lectio.py`
- Left other YAML specs loaded for legacy Studio until Phase 09

## Prompt changes
- none

## Contract/schema changes
- Resource-spec version bump `lesson` `1.0` → `1.1` (comment + version field only; role grammar unchanged)
- No Lectio contract edits

## API changes
- none (HTTP)

## DB/migration changes
- none

## Tests added
- `backend/tests/resource_specs/test_candidates.py`
  - primary resource is lesson + required arc
  - every lesson.yaml component exists in Lectio planner_index
  - every required role has non-empty legal candidates
  - deterministic across calls
  - forbidden / generation-excluded / manual-only / page-pseudo do not leak
  - budget exhaustion filter + max_per_section metadata

## Commands/results

| Command | Result |
|---|---|
| `cd backend && uv run pytest tests/resource_specs/ -q --tb=short` | **14 passed**, 1 warning; exit 0 |

## Failure-injection results
- N/A (Phase 01)

## Remaining legacy dependencies
- Studio still allows non-lesson resource types in UI (Phase 09 cutover)
- Stage 1 still selects components (Phase 02 intent)
- Selector not yet wired to this helper (Phase 03)

## Deviations
- Generation-excluded interpreted as Lectio `writer_excluded=True` plus `MANUAL_ONLY_COMPONENT_IDS` (diagrams/simulations stay out of AI content candidate sets; visual lane still owns them later)
- `max_per_section` is attached as selector metadata; only values `<= 0` remove a candidate (normal caps of `1` do not)

## Unexpected findings
- none blocking

## GO / NO-GO
**GO** — Code deterministically produces legal candidate sets for every lesson role; no illegal/manual/page-pseudo leak; lesson is primary/default resource grammar.
