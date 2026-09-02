# Phase 10 — Deterministic and Mocked E2E Acceptance
## Goal
Prove new architecture before live Codex computer-use verification.

Use the same general lesson spec for at least: math equivalent ratios, science plants/light, history/social studies causal/chronological concept, English concept/analysis.
Capture intent plan, candidate sets, component choices, canonical execution plan, work orders and final LessonDocument.

Inject the full failure matrix.

Mocked E2E:
```text
unit objective → lesson context → spec → intent plan → teacher approval fixture → constrained selection → work orders → mocked writers/items/visuals → validation → one repair → checkpoints → worker resume → LessonDocument → Builder load → edit/save/reload → render/PDF integration where available
```

Run full backend tests, DB/migration tests available locally, frontend tests/check/build, lint/typecheck scripts, new runtime suites and dead-code/import checks.

Write `artifacts/reports/FINAL_MIGRATION_REPORT.md` covering architecture, changes, tests, deletions, reuse, limitations, strict-tool deferral, and Codex live handoff.

## Gate
No known deterministic/mocked blocker remains; only live-provider/browser uncertainty is left for Codex.
