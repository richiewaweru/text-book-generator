# Failure Injection Matrix
| Scenario | Expected behavior |
|---|---|
| LLM timeout | transport retry; no repair budget |
| 429 | rate retry/backoff |
| provider 500 | transport retry |
| malformed structured output | model-output retry |
| invalid comparison-grid structure | component-scoped repair |
| extra field | exact Lectio validation/repair policy |
| missing required field | scoped repair |
| repair remains invalid | bounded failure; siblings ready |
| TypeError/NameError | terminal code error, no LLM retry |
| optional visual fails | text stays available; visual retryable/failed |
| required visual fails | only dependent readiness blocked |
| crash after 3/6 blocks | resume from checkpoints |
| lease expires | new worker reclaims |
| old worker returns | late write rejected |
| duplicate start/retry | idempotent |
| plan revision changes | stale output rejected |
| teacher edits in-flight block | human edit wins |
| SSE disconnect | poll/snapshot catches up |
| browser reload | Builder reconstructs state |
| backend restart | worker reclaims/resumes |
| one component fails | no whole-lesson regeneration |
| terminal failure | no infinite UI spinner |
