# Teacher Studio: Complete Logic & Data Flow Guide

This guide explains every file in the Teacher Studio implementation, what it does, and how data flows from frontend to backend and back.

---

## High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ FRONTEND (Svelte)                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  /studio route                                                   │
│      ↓                                                            │
│  TeacherStudioFlow.svelte (orchestrator)                         │
│      ├─ IntentForm.svelte (teacher input capture)                │
│      ├─ PlanStream.svelte (SSE streaming progress)               │
│      ├─ PlanReview.svelte (edit & approve)                       │
│      └─ GenerationView.svelte (live generation)                  │
│      ↓                                                            │
│  Studio store (studio.ts) — holds all state                      │
│      ↓                                                            │
│  Brief API client (brief.ts)                                     │
│      ├─ POST /api/v1/brief/stream (fetch + ReadableStream)       │
│      ├─ POST /api/v1/brief/commit                                │
│      └─ GET /api/v1/contracts                                    │
│                                                                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│ BACKEND (Python FastAPI)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  brief.py routes                                                │
│      ├─ POST /api/v1/brief/stream                                │
│      │   ├─ input: StudioBriefRequest (JSON)                     │
│      │   ├─ action: start PlanningService.plan()                 │
│      │   └─ output: SSE stream                                   │
│      ├─ POST /api/v1/brief/commit                                │
│      │   ├─ input: PlanningGenerationSpec (JSON)                 │
│      │   ├─ action: validate + call generation.py bridge         │
│      │   └─ output: GenerationAcceptedResponse                   │
│      └─ GET /api/v1/contracts                                    │
│          └─ output: list[PlanningTemplateContract]               │
│      ↓                                                            │
│  planning/ package (deterministic planning pipeline)             │
│      ├─ models.py (all data models)                              │
│      ├─ normalizer.py (default resolution)                       │
│      ├─ template_scorer.py (template selection)                  │
│      ├─ section_composer.py (section layout)                     │
│      ├─ visual_router.py (visual policy)                         │
│      ├─ prompt_builder.py (LLM refinement)                       │
│      ├─ fallback.py (safe defaults when LLM fails)               │
│      └─ service.py (orchestrator + event emission)               │
│      ↓                                                            │
│  generation.py (bridge to pipeline)                              │
│      └─ maps PlanningGenerationSpec → PipelineRequest            │
│      ↓                                                            │
│  pipeline/ (existing generation engine)                          │
│      └─ runs the actual textbook generation                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend: File-by-File Breakdown

### 1. `frontend/src/routes/studio/+page.svelte`

**Purpose:** Route entry point for `/studio`.

**What it does:**
- Renders the `TeacherStudioFlow` component
- SvelteKit route file (empty wrapper, component is the real work)

```svelte
<TeacherStudioFlow />
```

**Data flow:** None (just a router).

---

### 2. `frontend/src/lib/components/studio/TeacherStudioFlow.svelte` (396 lines)

**Purpose:** Top-level orchestrator. Manages the 4 states and routes between them.

**What it does:**
1. Initializes by loading contracts from backend (`listContracts()`)
2. Routes between 4 states:
   - `idle`: show `IntentForm`
   - `planning`: show `PlanStream` with SSE events coming in
   - `reviewing`: show `PlanReview` where teacher edits
   - `generating`: show `GenerationView` for live generation
3. Handles user actions: plan, commit, retry, reset
4. Manages SSE consumption and error states

**Key state variables:**
- `studioState`: current stage
- `planningError`: if planning failed
- `commitError`: if commit failed
- `committing`: loading state for commit button

**Key functions:**
- `loadContractCatalog()` — GET `/api/v1/contracts`, store in `contracts` store
- `handlePlan()` — GET form data, call `streamPlan()`, consume SSE events, update store
- `handleCommit()` — call `commitPlan()`, on success transition to generating
- `handleRetryPlanning()` — go back to idle, keep draft
- `handleTemplateSwap()` — call `swapTemplateInSpec()` to re-map components

**Data flow:**
```
TeacherStudioFlow
  ↓ loads
  GET /api/v1/contracts
  ↓
  contracts[] store updated
  ↓
  IntentForm submitted
  ↓
  briefDraft store updated
  ↓
  handlePlan() called
  ↓
  POST /api/v1/brief/stream + briefDraft
  ↓
  SSE: template_selected, section_planned[], plan_complete/plan_error
  ↓
  planDraft store updated as events arrive
  ↓
  studioState = 'reviewing'
  ↓
  PlanReview shows editedSpec
  ↓
  commitPlan() called
  ↓
  POST /api/v1/brief/commit + editedSpec
  ↓
  studioState = 'generating'
```

---

### 3. `frontend/src/lib/components/studio/IntentForm.svelte` (765 lines)

**Purpose:** Form for teacher to input lesson intent, audience, signals, preferences, constraints.

**What it does:**
1. Renders 5 input sections:
   - Intent (text input): "What do you want to teach?"
   - Audience (text input): "Who is this for?"
   - Prior knowledge / extra context (collapse, textareas)
   - Learning signals (chips): topic type, learning outcome, class style, format
   - Delivery preferences (dropdowns): tone, reading level, explanation style, example style, brevity
   - Constraints (checkboxes): emphasize practice, keep short, include visuals, optimize for print
2. Validates before submit: intent and audience required
3. Updates `briefDraft` store as user types
4. Emits `onSubmit` callback when submit clicked

**Key reactive state:**
- `showPriorKnowledge`: collapse/expand prior knowledge section
- `showPreferences`: collapse/expand preferences section
- `validationMessage`: error message
- `signalWarning`: warning if no signals selected

**Key functions:**
- `updateBrief(patch)` — merge patch into `briefDraft` store
- `updateSignals(key, value)` — update signals in store
- `updatePreferences(key, value)` — update preferences in store
- `updateConstraints(key, value)` — update constraints in store
- `handleSubmit()` — validate & emit `onSubmit` callback

**Data structure it creates:**
```typescript
UserBriefDraft {
  intent: string
  audience: string
  prior_knowledge: string
  extra_context: string
  signals: {
    topic_type: "concept" | "process" | "facts" | "mixed" | null
    learning_outcome: "understand-why" | "be-able-to-do" | "remember-terms" | "apply-to-new" | null
    class_style: [] // up to 3 of: "needs-explanation-first", "tries-before-told", etc.
    format: "printed-booklet" | "screen-based" | "both" | null
  }
  preferences: {
    tone: "supportive" | "neutral" | "rigorous"
    reading_level: "simple" | "standard" | "advanced"
    explanation_style: "concrete-first" | "concept-first" | "balanced"
    example_style: "everyday" | "academic" | "exam"
    brevity: "tight" | "balanced" | "expanded"
  }
  constraints: {
    more_practice: boolean
    keep_short: boolean
    use_visuals: boolean
    print_first: boolean
  }
}
```

**Data flow:**
```
User types in form
  ↓
  oninput/onchange handlers fire
  ↓
  updateBrief/updateSignals/updatePreferences/updateConstraints
  ↓
  briefDraft store updated
  ↓
  form re-renders with new values (Svelte reactivity)
  ↓
  User clicks "Build lesson plan"
  ↓
  handleSubmit() calls onSubmit callback
  ↓
  TeacherStudioFlow.handlePlan() invoked
```

---

### 4. `frontend/src/lib/components/studio/PlanStream.svelte` (475 lines)

**Purpose:** Show real-time planning progress with streamed sections arriving one by one.

**What it does:**
1. Shows a progress bar that fills as events arrive
2. Shows the chosen template name + fit score
3. Shows sections as they arrive with animation
4. Shows a "pending" placeholder for the next section
5. Shows error state if planning failed

**Key reactive state:**
- `planDraft` store (subscribed to): `template_decision`, `sections[]`, `is_complete`, `warning`, `error`
- `errorMessage` prop: passed from parent if planning failed
- `progressValue` derived: calculates % based on sections, template, and completion

**Key logic:**
```typescript
const progressValue = $derived.by(() => {
  if ($planDraft.is_complete) return 100;        // done!
  if (errorMessage) return 80;                   // error state
  if (!$planDraft.template_decision) return 18;  // template scoring
  return Math.min(86, 34 + $planDraft.sections.length * 15); // sections arriving
});
```

**Visual elements:**
- Status pill: "Live planning" or "Planning interrupted"
- Progress bar: width = progressValue%
- Template badge: chosen template name, fit score, rationale
- Section list: numbered cards with role pill, title, objective, components
- Pending section placeholder: shows ".." as order, grayed out

**Data flow:**
```
TeacherStudioFlow calls streamPlan()
  ↓
  POST /api/v1/brief/stream + briefDraft
  ↓
  SSE event: template_selected
  ↓
  TeacherStudioFlow calls setTemplateDecision()
  ↓
  planDraft store updated
  ↓
  PlanStream reacts: template badge appears, progress jumps
  ↓
  SSE event: section_planned
  ↓
  TeacherStudioFlow calls appendPlannedSection()
  ↓
  planDraft.sections[] grows
  ↓
  PlanStream reacts: new section card appears with animation
  ↓
  (repeat for each section)
  ↓
  SSE event: plan_complete
  ↓
  TeacherStudioFlow calls completePlanning()
  ↓
  planDraft.is_complete = true
  ↓
  PlanStream reacts: progress bar jumps to 100%, view transitions to review
```

---

### 5. `frontend/src/lib/components/studio/PlanReview.svelte` (641 lines)

**Purpose:** Let teacher review the plan, edit titles, swap templates, adjust focus notes.

**What it does:**
1. Shows the approved plan structure (read-only template decision)
2. For each section:
   - Show title (editable)
   - Show role (read-only badge)
   - Show focus note (editable)
   - Show selected components (edit button?)
   - Show visual policy indicator
3. Show template swap picker (sidebar or modal)
4. Show commit button ("Generate lesson")
5. Show "← Edit intent" button to go back

**Key state:**
- `editedSpec` store (subscribed to): the current working spec
- `catalogError` prop: error loading templates
- `busy` prop: commit is in progress
- `errorMessage` prop: commit failed

**Key functions:**
- `handleTitleChange(sectionId, newTitle)` — call `updateSection()` in store
- `handleFocusChange(sectionId, newFocus)` — call `updateSection()` in store
- `handleTemplateSwap(newContract)` — call `swapTemplateInSpec()`, updates editedSpec
- `handleCommit()` — parent calls `commitPlan()` via prop
- `handleBack()` — parent calls `returnToIdle()` via prop

**Data flow:**
```
PlanReview mounted
  ↓
  shows editedSpec (from store)
  ↓
  Teacher edits title
  ↓
  handleTitleChange() → store.updateSection()
  ↓
  editedSpec.sections[i].title updated
  ↓
  PlanReview re-renders with new title
  ↓
  (teacher swaps template)
  ↓
  handleTemplateSwap(newContract)
  ↓
  swapTemplateInSpec(editedSpec, newContract)
  ↓
  new editedSpec created with:
    - template_id changed
    - sections re-mapped to new template components
    - committed_budgets updated
  ↓
  editedSpec store updated
  ↓
  PlanReview re-renders with new template info
  ↓
  Teacher clicks "Generate lesson"
  ↓
  handleCommit() calls parent callback
  ↓
  TeacherStudioFlow.handleCommit() called
  ↓
  commitPlan(editedSpec) called
```

---

### 6. `frontend/src/lib/components/studio/GenerationView.svelte` (895 lines)

**Purpose:** Show live generation progress inside the studio workspace.

**What it does:**
1. Connects to the generation SSE stream
2. Renders sections progressively as they arrive
3. Shows each section with:
   - Title + role badge
   - Content (rendered Lectio components)
   - Progress indicator
4. Shows completion state

**Key state:**
- `accepted` prop: the `GenerationAcceptedResponse` from commit
- `generationState` store: document, connection status, sections[]

**Key logic:**
- Connect to generation SSE using `buildGenerationEventsUrl(accepted.generation_id)`
- Consume events and update store
- Re-render as sections arrive

**Data flow:**
```
PlanReview calls commitPlan(editedSpec)
  ↓
  POST /api/v1/brief/commit + editedSpec
  ↓
  Returns GenerationAcceptedResponse
  ↓
  TeacherStudioFlow calls setGenerationAccepted()
  ↓
  generationState.accepted = response
  ↓
  studioState = 'generating'
  ↓
  GenerationView mounted
  ↓
  connects to SSE using response.events_url
  ↓
  generation events arrive (section_started, section_completed, etc.)
  ↓
  sections render progressively
  ↓
  generation_complete event
  ↓
  show completion state
```

---

### 7. `frontend/src/lib/stores/studio.ts` (187 lines)

**Purpose:** Central state management for the studio. All state lives here.

**Store state:**
```typescript
studioState: writable<'idle' | 'planning' | 'reviewing' | 'generating'>
briefDraft: writable<UserBriefDraft>        // teacher's input, persists across transitions
planDraft: writable<PlanDraft>              // planning progress
editedSpec: writable<PlanningGenerationSpec | null>  // approved spec (teacher-edited)
planningMs: writable<number>                // how long planning took
contracts: writable<StudioTemplateContract[]>       // available templates
generationState: writable<StudioGenerationState>    // generation progress
```

**Key actions (functions that update state):**

| Function | What it does |
|----------|--------------|
| `resetPlanState()` | Clear planDraft, editedSpec, generationState (for retry) |
| `returnToIdle()` | Reset plan state + studioState = 'idle' (for "← Edit intent") |
| `beginPlanning()` | Clear planDraft, set studioState = 'planning' |
| `setTemplateDecision(decision, rationale, warning)` | Update planDraft.template_decision |
| `appendPlannedSection(section)` | Append to planDraft.sections[] |
| `completePlanning(spec, elapsedMs)` | Set planDraft.is_complete, editedSpec = spec (status='reviewed'), studioState = 'reviewing' |
| `failPlanning(message)` | Set planDraft.error = message |
| `updateSection(sectionId, updater)` | Update one section in editedSpec |
| `updateTemplateSelection(contract, sections)` | Change editedSpec.template_id + committed_budgets |
| `setContracts(contracts)` | Update contracts[] list |
| `setGenerationAccepted(response)` | Update generationState.accepted |

**Why stores instead of component state:**
- Multiple components need the same data (IntentForm, PlanStream, PlanReview, GenerationView)
- State persists across component remounting (teacher navigates away and back)
- Easier to debug (single source of truth)

---

### 8. `frontend/src/lib/api/brief.ts` (114 lines)

**Purpose:** HTTP client for the planning & generation routes.

**Functions:**

```typescript
async function streamPlan(brief: StudioBriefRequest): AsyncIterableIterator<PlanningEvent>
```
- POST `/api/v1/brief/stream` with JSON body
- Returns async iterator over SSE events
- Uses `fetch()` + `ReadableStream` (not EventSource, because POST body needed)
- Events are parsed JSON inside SSE data field

```typescript
async function commitPlan(spec: PlanningGenerationSpec): Promise<GenerationAcceptedResponse>
```
- POST `/api/v1/brief/commit` with JSON body
- Returns the response
- Throws `ApiError` if not 200

```typescript
async function listContracts(): Promise<StudioTemplateContract[]>
```
- GET `/api/v1/contracts`
- Returns list of templates

**Error handling:**
- `ApiError` class wraps HTTP errors with message
- TeacherStudioFlow catches and displays as user-facing messages

---

### 9. `frontend/src/lib/types/studio.ts` (227 lines)

**Purpose:** TypeScript types for all studio data.

**Key types:**
- `UserBriefDraft` — teacher's form input
- `PlanDraft` — planning progress (template, sections[], complete?, error?)
- `PlanningGenerationSpec` — the approved spec (matches backend model)
- `PlanningSectionPlan` — one section plan
- `StudioTemplateContract` — template metadata
- `StudioGenerationState` — generation progress
- `PlanningEvent` union type for SSE events: `TemplateSelectedEvent`, `SectionPlannedEvent`, `PlanCompleteEvent`, `PlanErrorEvent`

---

### 10. `frontend/src/lib/studio/template-swap.ts` (90 lines)

**Purpose:** Logic to swap templates during review and re-map section components.

**Function:**
```typescript
swapTemplateInSpec(
  current: PlanningGenerationSpec,
  newContract: StudioTemplateContract
): PlanningGenerationSpec
```

**What it does:**
1. Takes the current spec and a new template contract
2. For each section, re-maps `selected_components`:
   - Start with `always_present` from new template
   - Add components from current section that are in new template's `available_components`
   - Respect new template's `component_budget` (don't exceed max per component)
3. Updates `template_id`, `template_decision`, `committed_budgets`
4. Keeps `title`, `role`, `objective`, `focus_note` unchanged
5. Returns new spec

**Example:**
```
Current template: "guided-concept-path"
  - diagram-block component in section 0

New template: "open-canvas" (doesn't have diagram-block)
  - template-swap removes diagram-block
  - keeps other components that are available
  - updates component budget

Result: spec with diagram-block removed, components re-mapped
```

---

### 11. `frontend/src/lib/studio/presentation.ts` (81 lines)

**Purpose:** Helper functions to render planning data in UI.

**Functions:**
- `roleLabel(role)` — convert role enum to display text (e.g., "explain" → "Explanation")
- `roleTone(role)` — return CSS class for role badge color
- `componentLabel(component)` — convert component ID to display text
- `visualPolicyLabel(policy)` — render visual policy as human text

---

## Backend: File-by-File Breakdown

### 1. `backend/src/textbook_agent/interface/api/routes/brief.py` (242 lines)

**Purpose:** FastAPI routes for planning & generation.

**Routes:**

#### `POST /api/v1/brief` (deprecated)
```python
async def create_brief(brief: BriefRequest, ...) -> GenerationSpec
```
- Old synchronous endpoint
- Sends `Deprecation` header
- Used by legacy code; Teacher Studio uses `/stream` + `/commit` instead

#### `POST /api/v1/brief/stream` ⭐
```python
async def stream_brief(brief: StudioBriefRequest, ...) -> StreamingResponse
```

**What it does:**
1. Receives `StudioBriefRequest` (intent, audience, signals, preferences, constraints)
2. Loads contracts via `list_template_ids()` + `get_contract()`
3. Creates a `PlanningService` instance
4. Calls `service.plan(brief, contracts, model, run_llm_fn, emit, ...)`
5. Streams SSE events back to client:
   - `template_selected` — template chosen
   - `section_planned` — each section arrives
   - `plan_complete` — full spec returned
   - `plan_error` — fallback spec on LLM failure

**Data flow:**
```
POST /api/v1/brief/stream + StudioBriefRequest
  ↓
  async def stream() generator:
    queue = asyncio.Queue()

    async def emit(payload): queue.put(payload)

    async def run():
      spec = await service.plan(brief, ..., emit=emit)
      queue.put({event: 'plan_complete', data: {spec}})
    ↓
    [background task] run()  (starts planning)
    ↓
    while True:
      payload = await queue.get()
      yield SSE event line
  ↓
  StreamingResponse(stream, media_type='text/event-stream')
```

**Key detail:** Uses async queue for decoupling:
- `run()` (planning) emits events to queue
- `stream()` (HTTP) pulls from queue and sends to client
- If planning is slow, SSE stream doesn't block

#### `GET /api/v1/contracts` ⭐
```python
async def list_contracts(...) -> list[PlanningTemplateContract]
```
- Returns all live-safe templates
- Frontend loads on mount

#### `POST /api/v1/brief/commit` ⭐
```python
async def commit_brief(spec: PlanningGenerationSpec, ...) -> GenerationAcceptedResponse
```

**What it does:**
1. Validate template/preset combination — if invalid, return HTTP 422
2. Load user profile
3. Mark spec as `status='committed'`
4. Call `enqueue_generation()` helper from `generation.py` to:
   - Map `PlanningGenerationSpec` → `PipelineRequest` via bridge
   - Enqueue to pipeline
   - Return generation ID + SSE URLs

**Data flow:**
```
POST /api/v1/brief/commit + PlanningGenerationSpec
  ↓
  validate_preset_for_template(template_id, preset_id)
  ↓
  if invalid: return HTTP 422
  ↓
  profile = await _load_profile(user)
  ↓
  committed = spec.model_copy(update={status: 'committed'})
  ↓
  await enqueue_generation(
    subject=committed.source_brief.intent,
    context=_context_from_planning_spec(committed),
    section_plans=_pipeline_sections_from_planning_spec(committed),
    planning_spec_json=committed.model_dump_json(),
    ...
  )
  ↓
  Returns GenerationAcceptedResponse(generation_id, events_url, ...)
```

---

### 2. `backend/src/planning/models.py` (254 lines)

**Purpose:** Pydantic models for all planning data.

**Key models:**

| Model | Purpose |
|-------|---------|
| `StudioBriefRequest` | Teacher's form input (intent, audience, signals, preferences, constraints) |
| `TeacherSignals` | Topic type, learning outcome, class style, format |
| `DeliveryPreferences` | Tone, reading level, explanation style, example style, brevity |
| `TeacherConstraints` | More practice, keep short, use visuals, print first |
| `NormalizedBrief` | Resolved signals, directives, keyword profile, scope warning |
| `GenerationDirectives` | Tone profile, reading level, explanation style, example style, scaffold level, brevity |
| `PlanningTemplateContract` | Template metadata from Lectio |
| `PlanningSignalAffinity` | Scoring weights for signals |
| `PlanningSectionPlan` | One section: id, order, role, title, objective, focus_note, components, visual_policy, rationale |
| `VisualPolicy` | required, intent, mode, goal, style_notes |
| `TemplateDecision` | chosen_id, chosen_name, rationale, fit_score, alternatives[] |
| `PlanningGenerationSpec` | Full planning output: template_id, sections[], directives, warning, status, source_brief |

**Important validators:**
- `VisualPolicy._mode_required_when_visual_required()` — rejects required=True with missing mode/intent
- `PlanningSectionPlan._trim_optional_text()` — strips whitespace from optional fields
- `PlanningGenerationSpec._validate_sections()` — ensures sections are ordered 1, 2, 3, ...

---

### 3. `backend/src/planning/normalizer.py` (104 lines)

**Purpose:** Resolve unset signals to defaults, derive generation directives.

**Function:**
```python
def normalize_brief(brief: StudioBriefRequest) -> NormalizedBrief
```

**What it does:**
1. **Resolve signal defaults:** If teacher didn't pick a topic type, infer from intent text
   - Uses keyword matching (e.g., "steps", "process" → "process" type)
   - Falls back to "concept"
2. **Derive directives:** Map signals + preferences to generation directives
   - `scaffold_level` (high/medium/low) based on class style + tone
   - `tone_profile` = teacher's tone preference
   - `explanation_style` = teacher's preference
   - etc.
3. **Extract keyword profile:** Split intent into keywords for visual routing
4. **Flag scope warnings:** If intent is very long or contradicts signals, add warning

**Example:**
```
Input:
  intent: "Teach photosynthesis to Year 5 students"
  signals.topic_type: null (not set)
  constraints.use_visuals: true

Output NormalizedBrief:
  resolved_topic_type: "concept"  (inferred from intent)
  resolved_learning_outcome: "understand-why"  (default)
  directives.scaffold_level: "high"  (use_visuals constraint)
  keyword_profile: ["photosynthesis", "year", "5", ...]
```

---

### 4. `backend/src/planning/template_scorer.py` (215 lines)

**Purpose:** Choose the best template for the normalized brief.

**Function:**
```python
def choose_template(
  brief: NormalizedBrief,
  contracts: list[PlanningTemplateContract]
) -> tuple[PlanningTemplateContract, TemplateDecision]
```

**What it does:**
1. **Score each template** based on:
   - `signal_affinity`: How well template matches teacher's signals
     - Example: if topic_type="concept" and template has affinity {concept: 0.9}, score += 0.9
   - Metadata fallback: If affinity is empty, use template's `best_for`, `tags`, `not_ideal_for`
     - Example: if teacher wants "process" and template is tagged "procedure", score += 0.7
2. **Pick the highest-scoring template**
3. **Create TemplateDecision** with:
   - chosen_id, chosen_name, rationale
   - fit_score (0.0-1.0)
   - alternatives[] (other templates ranked)

**Example:**
```
Brief: topic_type="process", learning_outcome="be-able-to-do"

Template "Procedure":
  signal_affinity: {topic_type: {process: 0.9}, learning_outcome: {be-able-to-do: 0.8}}
  Score = 0.9 + 0.8 = 1.7
  Fit score = 0.85 (normalized)

Template "Concept Path":
  signal_affinity: {topic_type: {process: 0.3}, learning_outcome: {be-able-to-do: 0.6}}
  Score = 0.3 + 0.6 = 0.9
  Fit score = 0.45 (normalized)

Winner: "Procedure" (fit_score=0.85)
Alternative: "Concept Path" (fit_score=0.45)
```

---

### 5. `backend/src/planning/section_composer.py` (186 lines)

**Purpose:** Deterministically build the lesson structure: sections + components.

**Function:**
```python
def compose_sections(
  brief: NormalizedBrief,
  contract: PlanningTemplateContract
) -> list[PlanningSectionPlan]
```

**What it does:**
1. **Decide how many sections:** Usually 3-4 based on constraints
   - If `keep_short`, maybe 3 sections
   - If `more_practice`, might add a practice section
2. **Assign roles:** Use template's `section_role_defaults`
   - Example: role "intro" always gets ["hook-hero", "explanation-block"]
   - role "practice" always gets ["practice-stack"]
3. **Respect component budget:** Don't exceed `component_budget`
   - Example: if budget says max 1 diagram, don't put diagram in 2 sections
4. **Resolve constraints:**
   - If `use_visuals`, add visual components
   - If `print_first`, prefer text-friendly components
5. **Build PlanningSectionPlan** for each section with:
   - order (1, 2, 3, ...)
   - role (intro, explain, practice, summary, etc.)
   - selected_components (starting with always_present, adding optional)
   - title (placeholder: "Section 1", etc.)
   - objective (empty, will be filled by LLM)

**Example:**
```
Input contract "Guided Concept Path":
  section_role_defaults: {
    intro: ["hook-hero", "explanation-block"],
    explain: ["diagram-block", "worked-example-card"],
    summary: ["summary-block", "what-next-bridge"]
  }
  component_budget: {diagram-block: 1, worked-example-card: 1}

Output sections:
  Section 1 (order=1, role="intro"):
    selected_components: ["hook-hero", "explanation-block"]
  Section 2 (order=2, role="explain"):
    selected_components: ["diagram-block", "worked-example-card"]
  Section 3 (order=3, role="summary"):
    selected_components: ["summary-block", "what-next-bridge"]

Result: valid section layout respecting budget (diagram in 1 section only)
```

---

### 6. `backend/src/planning/visual_router.py` (87 lines)

**Purpose:** Decide which sections get visuals and what kind.

**Function:**
```python
def route_visuals(
  brief: NormalizedBrief,
  contract: PlanningTemplateContract,
  sections: list[PlanningSectionPlan]
) -> list[PlanningSectionPlan]
```

**What it does:**
1. For each section, decide if it should have a visual:
   - If section role is "visual", "process", "compare", "discover" → needs visual
   - If constraint `use_visuals` is set → add visuals
   - If section has visual components (diagram-block, etc.) → decide visual policy
2. For sections that need visuals, set `visual_policy`:
   - **intent:** Why the visual (explain_structure, show_realism, demonstrate_process, compare_variants)
   - **mode:** How (svg or image)
     - svg if `print_first` constraint or printed-booklet format
     - image for spatial/realistic topics (check keyword profile)
   - **goal:** What the visual achieves (e.g., "Show the sequence so learner can follow each step")
   - **style_notes:** How to render it (e.g., "Clean structural diagram" for svg)

**Example:**
```
Input section (role="process", components include "process-steps"):
  visual_policy: null

Keyword profile has: ["photosynthesis", "steps", "cycle"]  (spatial)
Constraints: {print_first: false}

Decision:
  intent = "demonstrate_process" (role is process)
  mode = "image" (spatial topic, not printing)
  goal = "Show the sequence..."
  style_notes = "...educational image..."

Output section:
  visual_policy: VisualPolicy(
    required=true,
    intent="demonstrate_process",
    mode="image",
    ...
  )
```

---

### 7. `backend/src/planning/prompt_builder.py` (92 lines)

**Purpose:** Single LLM call to refine titles and write lesson rationale.

**Function:**
```python
async def refine_plan_text(
  brief: NormalizedBrief,
  contract: PlanningTemplateContract,
  sections: list[PlanningSectionPlan],
  model: Any,
  run_llm_fn: Callable,
  ...
) -> PlanningRefinementOutput | None
```

**What it does:**
1. Build system prompt: "You refine lesson-plan text only. Don't change section count, roles, components, or visual policy."
2. Build user prompt with:
   - Intent, audience, prior knowledge, context
   - Template name
   - Current sections (order, role, components, objective)
3. Call LLM (pydantic-ai Agent) with structured output `PlanningRefinementOutput`
4. Validate output:
   - Section count matches (same as input)
   - All titles are non-empty
5. If validation fails, retry once
6. If both attempts fail, return None (fallback will be used)

**LLM produces:**
```json
{
  "lesson_rationale": "This lesson...",
  "warning": null,
  "sections": [
    {"title": "Why photosynthesis matters", "rationale": "Hook with relevance..."},
    {"title": "The photosynthesis process", "rationale": "Walk through steps..."},
    {"title": "Practice and reflection", "rationale": "Apply learning..."}
  ]
}
```

---

### 8. `backend/src/planning/fallback.py` (97 lines)

**Purpose:** Return a safe, reviewable spec when LLM fails.

**Function:**
```python
def build_fallback_spec(brief: StudioBriefRequest, contract: PlanningTemplateContract) -> PlanningGenerationSpec
```

**What it does:**
1. Takes the teacher's brief and chosen template
2. Builds sections from template's `section_role_defaults`
3. Fills titles with placeholder text: "Section 1", "Section 2", etc.
4. Copies objectives/focus from defaults
5. Sets `warning`: "Planning fell back to defaults. Review carefully."
6. Returns a valid `PlanningGenerationSpec` with status="draft"

**Why:** If the LLM call fails, we don't want to tell the teacher "sorry, try again." Instead, we give them a basic but valid lesson structure to review and edit.

**Example:**
```
Input brief: intent="Teach photosynthesis"
Input contract "Guided Concept Path"

Output spec:
  sections[0]: {
    order: 1,
    role: "intro",
    title: "Section 1",
    selected_components: ["hook-hero", "explanation-block"],
    visual_policy: null,
    rationale: "Introduction to the topic"
  }
  sections[1]: { ... }
  warning: "Planning fell back to defaults. Review carefully."
  status: "draft"
```

Teacher can then edit titles and proceed.

---

### 9. `backend/src/planning/service.py` (114 lines)

**Purpose:** Orchestrator that runs the full 6-step pipeline and emits SSE events.

**Class:** `PlanningService`

**Method:**
```python
async def plan(
  brief: StudioBriefRequest,
  contracts: list[PlanningTemplateContract],
  model: Any,
  run_llm_fn: Callable,
  emit: Callable,  # SSE event emitter
  llm_generation_mode: str = "draft"
) -> PlanningGenerationSpec
```

**What it does:**
1. Normalize brief → `NormalizedBrief`
2. Score and choose template → `(contract, TemplateDecision)`
3. Emit SSE event: `template_selected` with decision
4. Compose sections → `list[PlanningSectionPlan]`
5. Route visuals → `list[PlanningSectionPlan]` (with visual_policy set)
6. For each section added, emit SSE event: `section_planned`
7. Refine text (LLM) → `PlanningRefinementOutput` or fallback
8. Assemble final spec → `PlanningGenerationSpec` with status="draft"
9. Emit SSE event: `plan_complete` with full spec

**If LLM fails:**
1. Catch exception
2. Build fallback spec
3. Emit SSE event: `plan_error` with fallback spec + warning
4. Return fallback spec

**Data flow inside service:**
```
service.plan(StudioBriefRequest)
  ↓
  normalized = normalize_brief(brief)
  ↓
  contract, decision = choose_template(normalized, contracts)
  ↓
  emit({event: 'template_selected', data: {decision, lesson_rationale, warning}})
  ↓
  sections = compose_sections(normalized, contract)
  ↓
  sections = route_visuals(normalized, contract, sections)
  ↓
  for section in sections:
    emit({event: 'section_planned', data: {section}})
  ↓
  refined = await refine_plan_text(normalized, contract, sections, ...)
  ↓
  if refined is None:
    fallback = build_fallback_spec(brief, contract)
    emit({event: 'plan_error', data: {spec: fallback}})
    return fallback
  ↓
  spec = assemble_spec(decision, refined, sections, ...)
  ↓
  emit({event: 'plan_complete', data: {spec}})
  ↓
  return spec
```

---

### 10. `backend/src/textbook_agent/interface/api/routes/generation.py` (lines 167-210)

**Purpose:** Bridge between planning and pipeline. Maps `PlanningGenerationSpec` → `PipelineRequest`.

**Key functions:**

#### `_pipeline_section_from_planning(section, always_present)`
Converts `PlanningSectionPlan` → `SectionPlan` (pipeline's model)

**What it does:**
- Start with `always_present` components (required by template)
- Add selected components from planning section
- Deduplicate
- Extract focus: `focus_note or objective or rationale or title`
- Set needs_diagram, needs_worked_example based on components
- Return `SectionPlan` with all pipeline-expected fields

#### `_pipeline_sections_from_planning_spec(spec)`
Converts full spec's sections and wires continuity bridges

**What it does:**
- For each planning section, convert to pipeline section
- Set `bridges_from` = previous section's title
- Set `bridges_to` = next section's title
- Return list of `SectionPlan`

#### `_context_from_planning_spec(spec, subject)`
Builds the context string pipeline uses for generation

**What it does:**
- Start with subject (intent) + audience
- Add prior knowledge + extra context
- Add "Reviewed lesson plan:" section listing each section
- Include warning if planning flagged one
- Return as string

**Example output:**
```
Teach photosynthesis to Year 5 students
Audience: Mixed ability Year 5
Prior knowledge: Know about plants and sunlight
Additional context: 45-minute lesson, 25 students

Reviewed lesson plan:
Section 1: Why photosynthesis matters [intro] - Hook with real-world relevance
Section 2: The photosynthesis process [explain] - Walk through the steps
Section 3: Practice and reflection [practice] - Apply learning
```

---

## Complete Data Flow: From Intent to Generation

Let's trace one lesson from start to finish:

### Step 1: Teacher opens `/studio`

```
/studio route
  ↓
  TeacherStudioFlow.svelte mounted
  ↓
  loadContractCatalog()
  ↓
  GET /api/v1/contracts
  ↓
  brief.py:list_contracts()
    → list_template_ids()
    → get_contract() for each
    → returns list[PlanningTemplateContract]
  ↓
  contracts store updated
  ↓
  IntentForm renders with dropdown
```

### Step 2: Teacher fills form

```
IntentForm inputs:
  intent: "Teach photosynthesis to Year 5"
  audience: "Mixed ability Year 5 students"
  signals.topic_type: "process"
  signals.learning_outcome: "understand-why"
  constraints.use_visuals: true

Each change → updateBrief() → briefDraft store updated
```

### Step 3: Teacher clicks "Build lesson plan"

```
TeacherStudioFlow.handlePlan()
  ↓
  briefDraft = get(briefDraft)  // capture current state
  ↓
  studioState = 'planning'
  ↓
  streamPlan(briefDraft)  // POST /api/v1/brief/stream
  ↓
  brief.py:stream_brief(StudioBriefRequest)
    ↓
    contracts = _planning_live_safe_templates()
    ↓
    service = PlanningService()
    ↓
    queue = asyncio.Queue()
    ↓
    async def emit(payload): queue.put(payload)
    ↓
    [background] await service.plan(brief, contracts, ..., emit=emit)
    ↓
    [async loop] while True: payload = await queue.get(); yield SSE line
  ↓
  Frontend receives SSE stream
```

### Step 4: Planning runs, events stream in

```
service.plan(StudioBriefRequest)
  ↓
  Step 1: normalize_brief()
    input: StudioBriefRequest
    output: NormalizedBrief (resolved signals, directives, keywords)
  ↓
  Step 2: choose_template()
    input: NormalizedBrief, contracts[]
    scoring: topic_type="process" + learning_outcome="understand-why"
    winner: "Procedure" template (best fit)
    output: (contract, TemplateDecision)
  ↓
  emit({event: 'template_selected', data: {template_decision, lesson_rationale, warning}})
  ↓
  [Frontend receives event]
  setTemplateDecision(decision, rationale, warning)
  planDraft.template_decision = decision
  PlanStream re-renders: template badge appears, progress bar updates
  ↓
  Step 3: compose_sections()
    input: NormalizedBrief, contract
    role defaults from "Procedure" template:
      intro: ["hook-hero", "explanation-block"]
      process: ["process-steps", "diagram-block"]
      practice: ["practice-stack"]
      summary: ["summary-block", "what-next-bridge"]
    constraint use_visuals: add visual intent
    output: 4 PlanningSectionPlan
  ↓
  Step 4: route_visuals()
    input: sections[], brief.constraint.use_visuals=true
    for section with role="process":
      intent="demonstrate_process"
      mode="image"  (spatial keyword "photosynthesis" detected)
    output: sections[] with visual_policy set
  ↓
  for each section:
    emit({event: 'section_planned', data: {section}})
  ↓
  [Frontend receives 4 section_planned events]
    for each: appendPlannedSection(section)
    planDraft.sections[] grows
    PlanStream re-renders: section cards appear with animation
    progress bar advances
  ↓
  Step 5: refine_plan_text()
    input: normalized, contract, sections
    system prompt: "Refine titles only, don't change structure"
    user prompt: "Intent: Teach photosynthesis..."
    LLM call (pydantic-ai Agent):
      {
        "lesson_rationale": "This lesson...",
        "sections": [
          {"title": "Why plants need sunlight", "rationale": "..."},
          {"title": "How photosynthesis works", "rationale": "..."},
          {"title": "Practice identifying photosynthesis", "rationale": "..."},
          {"title": "Reflect on what we learned", "rationale": "..."}
        ]
      }
    validation: section count match? titles non-empty?
    output: PlanningRefinementOutput
  ↓
  Step 6: assemble spec
    combine decision + refined + sections
    status = "draft"
    output: PlanningGenerationSpec
  ↓
  emit({event: 'plan_complete', data: {spec: PlanningGenerationSpec}})
  ↓
  [Frontend receives plan_complete]
    completePlanning(spec)
    planDraft.is_complete = true
    editedSpec = spec (with status='reviewed')
    studioState = 'reviewing'
    PlanStream transitions to PlanReview
```

### Step 5: Teacher reviews and edits

```
PlanReview renders editedSpec
  - Section 1: "Why plants need sunlight" (teacher likes it)
  - Section 2: "How photosynthesis works" (teacher edits → "The photosynthesis process step-by-step")
  - Section 3: "Practice..." (teacher adds focus note: "Use image recognition activity")
  - Section 4: "Reflect..." (keep as is)

Teacher clicks "Generate lesson"
  ↓
  handleCommit() calls parent callback
```

### Step 6: Teacher commits

```
TeacherStudioFlow.handleCommit()
  ↓
  commitPlan(editedSpec)  // POST /api/v1/brief/commit
  ↓
  brief.py:commit_brief(PlanningGenerationSpec)
    ↓
    validate_preset_for_template(template_id="procedure", preset_id="blue-classroom")
    ✓ valid
    ↓
    committed = spec.model_copy(update={status: 'committed'})
    ↓
    await enqueue_generation(
      subject="Teach photosynthesis",
      context=_context_from_planning_spec(committed),
        → "Teach photosynthesis...\nReviewed lesson plan:\nSection 1: Why plants..."
      mode=GenerationMode.BALANCED,
      template_id="procedure",
      preset_id="blue-classroom",
      section_count=4,
      section_plans=_pipeline_sections_from_planning_spec(committed),
        → converts PlanningSectionPlan[] to SectionPlan[]
        → sets focus, wires bridges_from/bridges_to
      planning_spec_json=committed.model_dump_json(),
        → store full spec for auditing
    )
    ↓
    generation.py:enqueue_generation()
      ↓
      Create Generation entity with planning_spec_json column
      ↓
      Enqueue to pipeline
      ↓
      Returns GenerationAcceptedResponse(
        generation_id="gen-abc123",
        events_url="/api/v1/generations/gen-abc123/events",
        status="pending"
      )
  ↓
  Returns response to frontend
  ↓
  [Frontend receives response]
    setGenerationAccepted(response)
    studioState = 'generating'
    GenerationView mounted
```

### Step 7: Generation streams back in

```
GenerationView
  ↓
  connects to SSE: /api/v1/generations/gen-abc123/events
  ↓
  pipeline runs 6 nodes:
    1. CurriculumPlanner: produces CurriculumPlan
    2. ContentGenerator: produces SectionContent (per section) — uses context from planning bridge
    3. DiagramGenerator: produces SectionDiagram if visual_policy.required
    4. CodeGenerator: produces SectionCode
    5. Assembler: combines → RawTextbook
    6. QualityChecker: produces QualityReport
  ↓
  events stream back: section_started, section_completed, etc.
  ↓
  GenerationView re-renders as sections arrive
  ↓
  generation_complete event
  ↓
  GenerationView shows full lesson
```

---

## Summary Table

| Layer | Component | Input | Process | Output |
|-------|-----------|-------|---------|--------|
| **Frontend Form** | IntentForm.svelte | user clicks | captures form data | briefDraft store |
| **Frontend Orchestration** | TeacherStudioFlow.svelte | briefDraft | calls API | stagegation between 4 states |
| **API Client** | brief.ts | briefDraft or editedSpec | HTTP requests | SSE events or responses |
| **API Route** | brief.py:stream_brief | StudioBriefRequest | calls PlanningService | SSE stream |
| **Planning: Input** | normalizer.py | StudioBriefRequest | resolve defaults | NormalizedBrief |
| **Planning: Template** | template_scorer.py | NormalizedBrief + contracts | score by affinity | TemplateDecision |
| **Planning: Sections** | section_composer.py | NormalizedBrief + contract | compose roles + components | PlanningSectionPlan[] |
| **Planning: Visuals** | visual_router.py | brief + sections + contract | decide visual intent + mode | PlanningSectionPlan[] (with visual_policy) |
| **Planning: LLM** | prompt_builder.py | brief + contract + sections | call LLM to refine titles | PlanningRefinementOutput |
| **Planning: Assembly** | service.py | everything | orchestrate 6 steps | PlanningGenerationSpec |
| **Bridge** | generation.py | PlanningGenerationSpec | map to pipeline model | PipelineRequest |
| **Generation** | pipeline/ | PipelineRequest | generate lesson content | sections + report |
| **Frontend Viewer** | GenerationView.svelte | SSE events | stream sections | rendered lesson |

