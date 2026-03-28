# Handoff: Teacher Studio — Full Implementation Overview

**PRs:** #10, #11, #12
**Commits:** `072190c`, `634c1fb`, `25382cc`, `92b5e92`
**Date:** 2026-03-28
**Status:** Functional, with deferred items listed below

---

## What Is Teacher Studio

Teacher Studio is the lesson-creation workflow for teachers. Instead of the old 3-field form that made all planning decisions in a single LLM call, Teacher Studio provides:

1. **Intent capture** — structured form with topic/audience, learning signals (chips), delivery preferences (dropdowns), and constraint toggles
2. **Live planning** — deterministic pipeline that streams plan-building progress via SSE
3. **Review gate** — teacher sees the full plan, can edit titles/focus, swap templates, before committing
4. **In-place generation** — lesson generates inside the studio workspace with progressive section rendering

The canonical route is `/studio`.

---

## Backend: Planning Package

**Location:** `backend/src/planning/`

### Modules

| Module | Purpose |
|--------|---------|
| `models.py` | All planning Pydantic models: `StudioBriefRequest`, `NormalizedBrief`, `PlanningGenerationSpec`, `PlanningSectionPlan`, `VisualPolicy`, `TemplateDecision`, etc. |
| `normalizer.py` | Resolves defaults for unset signals, derives `GenerationDirectives` (tone, scaffold level, brevity), extracts keyword profile, flags scope warnings |
| `template_scorer.py` | Scores all live-safe templates against the normalized brief using `signal_affinity` dicts + metadata fallbacks. Returns chosen template + alternatives with fit scores |
| `section_composer.py` | Deterministic section layout: picks roles from template's `section_role_defaults`, assigns components respecting `component_budget` and `max_per_section`, handles constraint overrides (more_practice, keep_short, use_visuals) |
| `visual_router.py` | Decides which sections get visuals, what intent (explain_structure, show_realism, etc.), and what mode (svg vs image). Respects print_first constraint |
| `prompt_builder.py` | Single LLM call: refines section titles and writes lesson rationale. Validates output section count and non-empty titles |
| `fallback.py` | If the LLM call fails after 2 attempts, builds a valid `PlanningGenerationSpec` from template defaults with a warning |
| `service.py` | Orchestrates the pipeline: normalize → score → compose → route visuals → refine → assemble. Emits SSE events at each stage |

### Pipeline Flow

```
StudioBriefRequest
  → normalize_brief()         → NormalizedBrief
  → choose_template()         → (PlanningTemplateContract, TemplateDecision)
  → compose_sections()        → list[PlanningSectionPlan]
  → route_visuals()           → list[PlanningSectionPlan]  (with visual_policy set)
  → refine_plan_text()        → PlanningRefinementOutput   (LLM call)
  → assemble                  → PlanningGenerationSpec
```

Steps 1-4 are deterministic. Step 5 is the only LLM call. If it fails, `build_fallback_spec()` provides a reviewable spec with a warning.

### SSE Events Emitted

| Event | When | Payload |
|-------|------|---------|
| `template_selected` | After template scoring | `template_decision`, `lesson_rationale`, `warning` |
| `section_planned` | After each section is composed | `section` (PlanningSectionPlan) |
| `plan_complete` | After LLM refinement succeeds | `spec` (full PlanningGenerationSpec) |
| `plan_error` | After LLM refinement fails | `spec` (fallback), `warning` |

### Key Models

**`StudioBriefRequest`** — the teacher's input:
- `intent`, `audience` (required strings)
- `prior_knowledge`, `extra_context` (optional strings)
- `signals`: `TeacherSignals` (topic_type, learning_outcome, class_style[], format)
- `preferences`: `DeliveryPreferences` (tone, reading_level, explanation_style, example_style, brevity)
- `constraints`: `TeacherConstraints` (more_practice, keep_short, use_visuals, print_first)

**`PlanningGenerationSpec`** — the planning output:
- `template_id`, `preset_id`, `template_decision` (with alternatives and fit scores)
- `lesson_rationale`, `directives`, `committed_budgets`
- `sections[]`: each has `role`, `title`, `objective`, `focus_note`, `selected_components`, `visual_policy`, `generation_notes`
- `status`: `draft` → `reviewed` → `committed`
- `source_brief`: the original request

---

## Backend: Routes

**Location:** `backend/src/textbook_agent/interface/api/routes/brief.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/brief` | POST | **Deprecated.** Legacy synchronous brief endpoint. Returns `GenerationSpec`. Sends `Deprecation` header. |
| `/api/v1/brief/stream` | POST | New SSE planning endpoint. Accepts `StudioBriefRequest`, streams planning events, ends with `plan_complete` or `plan_error`. |
| `/api/v1/brief/commit` | POST | Accepts `PlanningGenerationSpec`, validates template/preset, maps to pipeline request, enqueues generation. Returns `GenerationAcceptedResponse`. |
| `/api/v1/contracts` | GET | Returns all live-safe `PlanningTemplateContract` objects for the frontend template picker. |

### Generation Bridge

**Location:** `backend/src/textbook_agent/interface/api/routes/generation.py:167-210`

The bridge maps planning output to pipeline input:
- `_pipeline_section_from_planning()` — converts `PlanningSectionPlan` → pipeline `SectionPlan`, resolving focus, components, visual/interaction policies, and continuity bridges
- `_pipeline_sections_from_planning_spec()` — converts full spec, wires `bridges_from`/`bridges_to` between adjacent sections
- `_context_from_planning_spec()` — builds the context string the pipeline uses for generation, including audience, prior knowledge, and section summaries

---

## Frontend: Components

**Location:** `frontend/src/lib/components/studio/`

| Component | Lines | Purpose |
|-----------|-------|---------|
| `TeacherStudioFlow.svelte` | ~400 | Orchestrator. Stage stepper, state routing, SSE consumption, commit/retry handlers |
| `IntentForm.svelte` | ~765 | Intent capture form. Signal chips, preference dropdowns, constraint toggles, validation |
| `PlanStream.svelte` | ~475 | Live planning view. Progress bar, template badge, section cards arriving with animation |
| `PlanReview.svelte` | ~640 | Review gate. Editable titles/focus, template swap picker, component chips, commit button |
| `GenerationView.svelte` | ~895 | In-place generation. SSE connection, progressive section rendering, completion state |

### State Management

**Location:** `frontend/src/lib/stores/studio.ts`

Svelte writable stores (not runes — cross-component state):
- `studioState`: `'idle' | 'planning' | 'reviewing' | 'generating'`
- `briefDraft`: `UserBriefDraft` — persists across state transitions (not reset on `returnToIdle`)
- `planDraft`: `PlanDraft` — template decision, sections[], is_complete, error, warning
- `editedSpec`: `PlanningGenerationSpec | null` — the teacher-editable spec (set on plan_complete with status='reviewed')
- `contracts`: `StudioTemplateContract[]` — loaded from `/api/v1/contracts`
- `generationState`: accepted response + document + connection banner

Key actions: `beginPlanning()`, `setTemplateDecision()`, `appendPlannedSection()`, `completePlanning()`, `failPlanning()`, `returnToIdle()`, `updateSection()`, `updateTemplateSelection()`

### API Client

**Location:** `frontend/src/lib/api/brief.ts`

- `streamPlan(brief)` — POST to `/api/v1/brief/stream`, returns async iterator of parsed SSE events via `fetch()` + `ReadableStream` (not `EventSource`, because POST body is needed)
- `commitPlan(spec)` — POST to `/api/v1/brief/commit`
- `listContracts()` — GET `/api/v1/contracts`

### Types

**Location:** `frontend/src/lib/types/studio.ts` (227 lines)

All studio-specific types mirroring the backend models: `UserBriefDraft`, `PlanDraft`, `PlanningGenerationSpec`, `PlanningSectionPlan`, `StudioTemplateContract`, `StudioGenerationState`, signal/preference/constraint literal unions, SSE event types.

### Template Swap

**Location:** `frontend/src/lib/studio/template-swap.ts`

`swapTemplateInSpec(spec, newContract)` — when the teacher picks a different template during review, this function re-maps section components to the new template's available/required components and updates budgets.

---

## Route Structure

| Route | What renders |
|-------|-------------|
| `/studio` | `TeacherStudioFlow.svelte` — full 4-state lesson creation workflow |
| `/dashboard` | Links to `/studio` for new lessons; shows generation history |
| `/textbook/[id]` | Read-only generation viewer (unchanged, still works) |

---

## Template Contracts

Templates are loaded from `backend/contracts/*.json`, generated by Lectio's `npm run export-contracts`. The planning layer uses extended fields:

| Field | Purpose |
|-------|---------|
| `signal_affinity` | `{ topic_type: {concept: 0.9, ...}, ... }` — scoring weights |
| `section_role_defaults` | `{ intro: ["hook-hero"], explain: ["diagram-block", ...] }` — default components per role |
| `component_budget` | `{ "diagram-block": 1 }` — max count across all sections |
| `max_per_section` | `{ "diagram-block": 1 }` — max count within one section |
| `available_components` | Full list of components this template supports |
| `always_present` | Components that must appear in every section plan |

Not all templates have full `signal_affinity` data yet. The scorer falls back to metadata matching (best_for, tags, intent) when affinity dicts are empty.

---

## How the Full Flow Works End-to-End

1. Teacher navigates to `/studio`
2. `TeacherStudioFlow` loads contracts from `/api/v1/contracts`
3. Teacher fills `IntentForm` — topic, audience, signals, preferences, constraints
4. Teacher clicks "Build lesson plan"
5. Frontend calls `streamPlan(brief)` → POST `/api/v1/brief/stream`
6. Backend runs the 6-step planning pipeline, emitting SSE events
7. Frontend shows `PlanStream` — progress bar fills, template badge appears, sections arrive one by one
8. On `plan_complete`, frontend transitions to `PlanReview`
9. Teacher reviews: edits titles/focus, optionally swaps template, adjusts sections
10. Teacher clicks "Generate lesson"
11. Frontend calls `commitPlan(spec)` → POST `/api/v1/brief/commit`
12. Backend validates template/preset, maps spec to pipeline request, enqueues generation
13. Frontend transitions to `GenerationView` — connects to generation SSE, renders sections progressively
14. On completion, teacher sees the full lesson in-place

---

## What's Left (Deferred)

| Item | Why deferred |
|------|--------------|
| Component-level editing in review | Complex drag-and-drop UX, not in MVP scope |
| Section retry/enhancement in generation view | Requires pipeline support for partial re-generation |
| Draft brief persistence | Needs backend storage; currently only persists in browser memory |
| Multi-lesson management | Future feature; `/studio` handles one lesson at a time |
| Native pipeline consumption of `PlanningGenerationSpec` | Would remove the bridge; requires pipeline-side changes |
| Visual asset generation from `visual_policy` | Pipeline doesn't generate images/SVGs yet; `visual_policy` is a specification only |
| Full `signal_affinity` in all templates | Needs Lectio export pipeline updates |
| `prior_knowledge` used in pipeline prompts | Field exists end-to-end but pipeline prompts don't use it yet |
