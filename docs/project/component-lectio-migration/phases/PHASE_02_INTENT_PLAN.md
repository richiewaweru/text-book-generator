# Phase 02 — Simplify Structural Planning into Intent Planning
## Goal
Decide what each lesson role must accomplish before choosing components.

## Reuse
Current StructuralPlan/LessonIntent/ConceptCard/anchor/learner context, structural planner infrastructure, validation/error feedback.

## Changes
1. Refactor Stage 1 output around ordered lesson roles/intent purposes.
2. Use resolved general lesson spec as allowed role grammar.
3. Output per role only what downstream needs: role, title where useful, concept-specific purpose, must-establish/misconception/transition/visual need where useful.
4. Remove broad component catalogue selection from Stage 1.
5. Stop injecting entire Lectio planner index if no longer needed.
6. Keep teacher approval/edit gate on this teaching sequence.
7. Deterministically validate role vocabulary, depth/count/order, objective ownership and path-approved objective.
8. Evolve current StructuralPlan if possible; only add IntentPlan if it materially clarifies ownership. Temporary adapters must be removed Phase 09.

## Tests
Same general spec across math ratios, science plants/light, history/social studies, English. Assert valid role sequences and concept-specific purposes without component choice.

## Gate
Stage 1 plans teaching sequence without full component-catalogue reasoning.
