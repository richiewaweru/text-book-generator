# Phase 03 — Constrained Component Selection and Canonical Execution Plan
## Goal
Choose best components from small legal sets and normalize into one code-owned execution plan.

## Reuse
`component-selector-v1.txt`, Lectio component metadata, current budgets/max-per-section/template constraints, useful current component-slot models.

## Flow
For each approved role:
1. compute legal candidates from Phase 01;
2. load lightweight metadata only for those candidates;
3. selector receives lesson context + role purpose + candidates + relevant card context + budget;
4. validate selector output;
5. code assigns stable block IDs, section IDs, positions and plan revision.

## Canonical execution artifact
Internal only; record generation/lesson ID, plan revision/hash, sections/positions/role, block IDs, selected component ID/purpose, document position, dependencies if required, lane/work kind where deterministic, template ID, budget state.

## Rules
Never select outside candidate set; reject duplicate section-field conflicts; enforce budgets/caps; prefer minimal component count; no exact schemas in selector prompt.

## Tests
Candidate violation, duplicate field, budget violation, deterministic IDs, misconception-vs-comparison selector case, four-subject general-spec cases, prompt contains only narrowed candidates.

## Gate
Approved intent plan → validated canonical execution plan without content generation.
