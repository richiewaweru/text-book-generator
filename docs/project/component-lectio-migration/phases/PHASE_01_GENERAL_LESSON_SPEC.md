# Phase 01 — Contract Authority and General Lesson Spec
## Goal
Make the existing general lesson spec the explicit production lesson grammar and prove all referenced components are legal.

## Reuse
Start from `resources/specs/lesson.yaml`, resource-spec schema/loader, Lectio planner index/template helpers. Do not create a parallel spec framework unless proven necessary.

## Changes
1. Clean/simplify `lesson.yaml` to agreed general lesson approach.
2. Keep broad orient/build/model/practice/close arc unless current equivalent vocabulary should remain.
3. Keep role candidate sets intentionally narrow.
4. Validate each candidate against Lectio planner index, template availability and generation/manual exclusions.
5. Add deterministic candidate intersection helper.
6. Remove duplicated component metadata where Lectio owns it.
7. Make lesson the primary/default resource spec; do not delete other specs yet.

## Tests
- every spec component exists in active Lectio contract;
- every required role has candidates;
- filters honor forbidden/template/manual-only/budgets;
- no unavailable media/manual components leak;
- no page pseudo-component appears.

## Gate
Code can deterministically produce legal candidate sets for every lesson role.
