# MASTER CURSOR PROMPT — Component Lectio Production Restructure

You are restructuring the current local checkout of `richiewaweru/text-book-generator`, expected branch `xplore`.

Read the full artifact pack before editing. Treat it as the implementation contract.

## Operating rules
1. Preserve all pre-existing dirty work. Never reset, clean or discard unrelated edits.
2. Phase 00 records actual local branch, HEAD, dirty state, migrations, routes, prompts, tests and runtime topology. The researched GitHub snapshot may be behind local code.
3. Work strictly phase-by-phase. Do not batch the migration.
4. At each phase end: run tests, write `artifacts/reports/phase-XX-verification.md`, mark GO/NO-GO, and fix NO-GO before continuing.
5. Prefer reuse/relocation over rewriting.
6. Do not create a second public lesson/document schema. Lectio contracts and `LessonDocument` remain authoritative.
7. Do not add page-oriented pseudo-components such as `prose`, `table`, `aside`, or `figure`.
8. Do not expose the full Lectio catalogue to the selector when the lesson spec can narrow it first.
9. Do not hard-code duplicate Lectio metadata already exported by Lectio.
10. Do not delete Builder or Builder-native functionality.
11. Do not delete V3 Studio before Phase 09 gates pass.
12. Do not add DeepSeek/OpenAI-compatible strict-tool schema enforcement in this round.
13. Do not introduce a database redesign. Reuse `GenerationModel`, `GenerationStepModel`, `chunked_state_json`, current revision fields and persistence unless a specific test proves a minimal additive migration is required.
14. No silent fallback to legacy generation after cutover.
15. No indefinite compatibility aliases. Remove dead legacy after callsites migrate.

## Canonical target flow
```text
UNIT PATH
  objective + prerequisites + sequence
      ↓
LESSON CONTEXT
  subject + grade + objective + learner context + duration
      ↓
GENERAL LESSON SPEC
  role purposes + legal component candidates
      ↓
INTENT / STRUCTURAL PLAN
  what each lesson role must accomplish
      ↓
TEACHER GATE
      ↓
CONSTRAINED COMPONENT SELECTION
  each role sees only legal candidates + lightweight Lectio metadata
      ↓
CANONICAL EXECUTION PLAN
  code-owned IDs + positions + legality + budgets + revision
      ↓
EXACT LECTIO CONTRACT LOOKUP
  selected components only
      ↓
WORK ORDERS
      ├── content lane
      ├── item/question lane
      └── visual lane
      ↓
VALIDATE → SCOPED REPAIR/RETRY → CHECKPOINT
      ↓
LECTIO LESSONDOCUMENT
      ↓
BUILDER (live + editable + durable)
      ↓
RENDER / PDF
```

## Ownership
- Unit planner: progression, lesson objective, prerequisites, ordering.
- General lesson spec: general pedagogical arc and role→eligible component constraints.
- Intent planner: concept-specific purpose of each lesson role.
- Component selector: local choice among already-narrowed legal components.
- Code: IDs, positions, candidate intersection, budgets, revision fencing, execution ownership, persistence.
- Lectio: component metadata, schemas, field contracts, formatting policy, document semantics.
- Writers: content only.
- Builder/human: edited document state; newer human revision beats stale generation.

## Phase order
00 Baseline/inventory
01 Contract authority + general lesson spec
02 Intent-plan simplification
03 Constrained component selection + canonical execution plan
04 Exact work orders + prompt migration + validation
05 Typed failures + retry/repair
06 Durable checkpoints + resume/idempotency
07 Worker lease + fencing
08 Direct LessonDocument + live Builder
09 Cutover + legacy/junk deletion
10 Full deterministic/mocked E2E acceptance

## Completion criteria
- lesson is the primary production resource;
- spec narrows candidates;
- selector sees only legal candidates;
- selected contracts come from Lectio exports;
- invalid component repair is local;
- transport retries do not consume repair budget;
- completed work survives restart;
- stale workers cannot overwrite newer work;
- Builder receives a valid `LessonDocument` directly;
- stale generator output cannot overwrite a newer Builder edit;
- polling/SSE reconnect reconstructs durable state;
- V3 Studio production orchestration and obsolete conversion/UI code are gone;
- no active production imports/callers remain for deleted code;
- backend tests, frontend tests/check/build and new acceptance suites pass.
