# Current → Target Map
| Current responsibility | Current area | Target owner | Phase |
|---|---|---|---|
| Resource shape | `resources/specs/*.yaml` | `lesson.yaml` primary general lesson spec | 01 |
| Broad Stage 1 planning | structural planner | intent/structural planning only | 02 |
| Component selection in broad plan | structural planner/selector concepts | constrained selector | 03 |
| Planner metadata | full planner index in Stage 1 | role candidate slice + Lectio metadata | 03 |
| Component cards | `contracts.lectio` | keep, selected-card lookup | 03-04 |
| Section brief expansion | section expander | selected work-order briefing or deterministic collapse if redundant | 04 |
| Writer schema hints | writer prompts | exact selected component contract | 04 |
| Lectio validation | `lectio_validation.py` | keep/complete | 04 |
| Retry loops | planning/runtime retry | typed failure policy | 05 |
| Validator feedback | planning retries | component repair service | 05 |
| Step persistence | GenerationStepModel | durable checkpoints | 06 |
| Broad state | generation/chunked JSON | explicit control state | 06 |
| In-process background tasks | Studio router | durable worker | 07 |
| In-memory ownership locks | Studio router | DB lease/fencing | 07 |
| V3 snapshot writer | V3GenerationWriter | runtime repository | 06-07 |
| V3 pack assembly | V3 assembly | direct LessonDocument assembly | 08 |
| V3→Builder adapter | Studio frontend adapter | delete | 08-09 |
| Polling/streaming | generic frontend | keep/adapt | 08 |
| Builder editing | Builder | keep + human revision fence | 08 |
| V3 Studio API | giant router | focused APIs/services | 09 |
| Session store | V3 Studio | delete | 09 |
| Studio UI | Studio routes/components | delete after parity | 09 |
| Non-lesson direct resources | primary resource selection | remove from primary flow; future derivatives | 09 |
