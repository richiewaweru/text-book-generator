# Legacy / Junk Deletion Map
A file is deletable only when its responsibility is obsolete or has a tested replacement.

## V3 Studio target
Before deleting, replace/extract: status/snapshot persistence, generation start/status/retry, visual regeneration, component/card repair still needed, telemetry, PDF invocation if coupled, stale-running recovery, history/detail endpoints required by UI.

Then remove giant orchestration router, in-memory background task retention, in-memory ownership locks, session store, obsolete DTO/prompt helpers and dead adapters.

## Non-lesson resource specs
Lesson is primary. Worksheet/quiz/exit-ticket/practice-set/quick-explainer/booklet become future derivatives.
- remove non-lesson choices from primary generation UI/API;
- do not build derivative generation in this migration;
- keep YAML only if explicitly useful for future derivative design or active tooling, otherwise park/delete and report.
- never keep an old direct-resource generation fallback hidden.

## Old planning artifacts
Review merge critic, knowledge-type classifier, old skeleton resources, legacy structural-plan adapters. Delete only after production callsite search shows zero use and the new path covers the responsibility.

For each deletion group report paths, old responsibility, replacement/reason obsolete, zero-caller search, and regression tests.
