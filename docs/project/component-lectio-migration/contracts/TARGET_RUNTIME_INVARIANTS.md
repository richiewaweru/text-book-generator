# Target Runtime Invariants
1. Unit planning never chooses Lectio components.
2. General lesson spec is the primary lesson resource spec.
3. Role/intent is decided before component selection.
4. Selector sees only candidates legal for role+template+budget.
5. Selection uses Lectio metadata, especially `cognitive_job`.
6. Full Lectio schemas are not needed for component choice.
7. Exact schemas are loaded only for selected components.
8. Stable block/section IDs are code-owned.
9. Execution order may be parallel; document order follows canonical Lectio/plan semantics.
10. A validated completed block/step is reusable progress.
11. Repair of one block does not regenerate valid siblings.
12. Transport and repair budgets are independent.
13. Stale workers cannot persist after losing ownership.
14. Stale generation cannot overwrite newer human edits.
15. Persistent state reconstructs current lesson after process/browser/SSE interruption.
16. Final artifact is a valid Builder-openable `LessonDocument`.
17. Builder manual edits, block AI generation and visual regeneration remain functional.
18. No fallback to removed V3 Studio after cutover.
19. Terminal runtime failure is persisted and visible.
20. Lectio metadata is not duplicated when the export already owns it.
