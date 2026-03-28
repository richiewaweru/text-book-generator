# Handoff: Teacher Studio + Planning Layer Audit & Fixes

**PR:** [#12](https://github.com/richiewaweru/text-book-generator/pull/12)
**Commit:** `92b5e92` — `fix(studio): harden planning layer and teacher studio integration`
**Date:** 2026-03-28
**Tests:** 19 passed (planning + brief), 0 regressions

---

## Context

The Teacher Studio and Planning Layer were implemented across three PRs:

| PR | Commit | What it did |
|----|--------|-------------|
| #10 | `072190c` | Initial teacher studio planning flow |
| #11 | `634c1fb` + `25382cc` | Full planning backend + frontend sub-components |
| #12 | `92b5e92` | Audit fixes (this handoff) |

The implementation added:
- **Backend:** `backend/src/planning/` package (8 modules: normalizer, template_scorer, section_composer, visual_router, prompt_builder, fallback, service, models)
- **Backend routes:** `POST /api/v1/brief/stream` (SSE), `POST /api/v1/brief/commit`, `GET /api/v1/contracts`
- **Frontend:** 5 sub-components (`IntentForm`, `PlanStream`, `PlanReview`, `GenerationView`, `TeacherStudioFlow`), dedicated store (`studio.ts`), types (`studio.ts`), API client (`brief.ts`), template-swap logic
- **Route:** `/studio` as the canonical teacher lesson-creation route

A deep audit was performed against the two source-of-truth proposals (`teacher-studio-ui-proposal.md` and `planning-layer-proposal.md`) plus HTML wireframes. This handoff covers the bugs found and fixes applied.

---

## What Was Fixed

### HIGH severity

#### 1. VisualPolicy model accepts invalid state
**File:** `backend/src/planning/models.py`
**Bug:** `VisualPolicy(required=True, mode=None)` was valid — downstream pipeline expects mode and intent to be set when `required=True`.
**Fix:** Added `@model_validator(mode="after")` that raises `ValueError` when `required=True` and either `mode` or `intent` is `None`.

#### 2. `/brief/commit` missing template/preset validation
**File:** `backend/src/textbook_agent/interface/api/routes/brief.py`
**Bug:** `commit_brief()` passed `template_id` and `preset_id` directly to `enqueue_generation()` without checking they form a valid combination. An invalid combo would fail deep inside the pipeline with an obscure error.
**Fix:** Added `validate_preset_for_template()` check at the top of the handler. Returns HTTP 422 with a clear message on invalid combos.

#### 3. IntentForm constraint checkboxes (false positive)
**File:** `frontend/src/lib/components/studio/IntentForm.svelte`
**Finding:** Originally flagged as unwired, but the implementation on main already had correct `onchange` handlers calling `updateConstraints()`. No fix needed.

### MEDIUM severity

#### 4. Generation bridge focus can be None
**File:** `backend/src/textbook_agent/interface/api/routes/generation.py:179`
**Bug:** The chain `section.focus_note or section.objective or section.rationale or section.title` could theoretically produce a falsy value if all fields were empty strings (title is required but could be whitespace-trimmed to empty by upstream).
**Fix:** Added `if not focus: focus = f"Section {section.order}"` guard after the chain.

#### 5. PlanStream progress bar never reaches 100%
**File:** `frontend/src/lib/components/studio/PlanStream.svelte`
**Bug:** Progress capped at 86% via `Math.min(86, ...)`. On `plan_complete`, the bar stayed at 86% before the view transitioned to review.
**Fix:** Added `if ($planDraft.is_complete) return 100;` as the first check in the derived progress value.

#### 6. IntentForm prior knowledge collapse state lost on return
**File:** `frontend/src/lib/components/studio/IntentForm.svelte`
**Bug:** `showPriorKnowledge` was initialized from a snapshot (`get(briefDraft)`) rather than the reactive store value. Functionally equivalent at mount time, but using the reactive `$briefDraft` is more idiomatic and consistent.
**Fix:** Changed to use `$briefDraft` directly in the `$state()` initializer.

#### 7. TeacherStudioFlow treats unknown SSE events as errors
**File:** `frontend/src/lib/components/studio/TeacherStudioFlow.svelte`
**Bug:** In the SSE event loop, any event that wasn't `template_selected`, `section_planned`, or `plan_complete` fell through to be cast as `PlanningErrorEvent`. This meant any future event type would crash the planning flow.
**Fix:** Wrapped the error handling in an explicit `if (event.event === 'plan_error')` check. Unknown events are now silently ignored with a comment noting forward compatibility.

### LOW severity

#### 8. visual_router.py return type annotations
**File:** `backend/src/planning/visual_router.py`
**Fix:** Changed `_visual_mode()` return from `str` to `PlanningVisualMode` and `_visual_intent()` from `str` to `PlanningVisualIntent`.

#### 9. prompt_builder.py title validation
**File:** `backend/src/planning/prompt_builder.py`
**Fix:** After validating section count match, added a check that each refined section has a non-empty title. Empty titles from the LLM now trigger a retry.

#### 10. visual_router.py spatial keyword coverage
**File:** `backend/src/planning/visual_router.py`
**Fix:** Expanded `_SPATIAL_HINTS` from 12 to 29 keywords. Added: geography, architecture, geology, organ, molecule, skeleton, volcano, ocean, continent, mountain, weather, circuit, engine, building, bridge, solar, galaxy.

#### 11. studio.ts status override comment
**File:** `frontend/src/lib/stores/studio.ts`
**Fix:** Added explanatory comment on the intentional `status: 'reviewed'` override in `completePlanning()`.

---

## Tests Added

| Test | File | What it covers |
|------|------|----------------|
| `test_visual_policy_rejects_mode_none_when_required` | `tests/planning/test_planning.py` | VisualPolicy model validator rejects invalid states |
| `test_section_count_boundaries` | `tests/planning/test_planning.py` | Section composer stays within 2-5 bounds |
| `test_empty_signal_affinity_scoring_uses_metadata` | `tests/planning/test_planning.py` | Template scorer handles contracts with empty affinity dicts |
| `test_section_focus_fallback_in_bridge` | `tests/planning/test_planning.py` | Bridge produces valid focus when optional fields are None |
| `test_commit_brief_starts_generation_with_committed_planning_spec` | `tests/interface/test_brief.py` | Updated to mock `validate_preset_for_template` |
| `test_commit_brief_rejects_invalid_template_preset_combination` | `tests/interface/test_brief.py` | Commit endpoint returns 422 on invalid combo |

---

## Files Changed

```
backend/src/planning/models.py                      (+6)
backend/src/planning/prompt_builder.py               (+3)
backend/src/planning/visual_router.py                (+23, -4)
backend/src/textbook_agent/interface/api/routes/brief.py (+6)
backend/src/textbook_agent/interface/api/routes/generation.py (+2)
backend/tests/interface/test_brief.py                (+15)
backend/tests/planning/test_planning.py              (+123)
frontend/src/lib/components/studio/IntentForm.svelte (+2, -5)
frontend/src/lib/components/studio/PlanStream.svelte (+3)
frontend/src/lib/components/studio/TeacherStudioFlow.svelte (+9, -6)
frontend/src/lib/stores/studio.ts                    (+1)
```

---

## Known Issues Not Addressed (Pre-existing)

- **Missing contracts directory in worktrees/CI:** `backend/contracts/` is generated by Lectio (`npm run export-contracts`), not committed. Tests in `test_generation_report_recorder.py` fail when this directory is absent. This is a test isolation issue, not a code bug.
- **Frontend type-check requires specific Node version:** `@sveltejs/vite-plugin-svelte@6.2.4` requires Node `^20.19 || ^22.12 || >=24`. Node v23.x is not supported.

---

## Deferred Items (From Proposals, Out of Scope)

These items are specified in the proposals but were not part of this fix pass:

- Component-level editing in review screen (drag to reorder, add/remove components per section)
- Section retry/enhancement controls in generation view
- Saving draft briefs for later resumption
- Multi-lesson management or lesson history
- Pipeline refactor to consume `PlanningGenerationSpec` natively (remove bridge mode)
- Visual asset pipeline (image/SVG generation from `visual_policy`)
- Full `signal_affinity` data in all 20+ template contracts (needs Lectio export work)
- `prior_knowledge` field integration into pipeline prompt context (field exists but pipeline doesn't use it)

---

## Architecture Notes

The planning package maintains strict import isolation:
- `planning/` never imports `pipeline/` or `textbook_agent/`
- `textbook_agent/` imports both `planning/` and `pipeline/`
- The bridge in `routes/generation.py` maps `PlanningGenerationSpec` → `PipelineRequest` with `PlanningSectionPlan` → `SectionPlan` conversion
- Role vocabulary expansion (9 planning roles vs 4 pipeline roles) is handled at the bridge level — the pipeline receives the planning role string and treats unknown roles as `develop`
