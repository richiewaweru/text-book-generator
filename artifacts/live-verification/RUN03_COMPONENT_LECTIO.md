# Run 3 — Component Lectio terminal reconciliation

This is sanitized local campaign evidence for generation `7623d9cc-378b-4a45-a649-31517bd5b240`. Prompts, learner identifiers, credentials, raw provider errors, and lesson/document text are intentionally omitted.

## Scope and disposition

- Verified source SHA: `9871fcaa09ed253069547bb08854bb17f5f44466`.
- Database: `textbook_agent_component_lectio_campaign` (PostgreSQL 16), migration `20260905_0034`.
- Persisted control marker: `pipeline=component_lectio`, `pipeline_version=1`.
- Generation mode: `v3`; requested/resolved template `guided-concept-path`; requested/resolved preset `v3-studio`; section count `5`.
- Terminal disposition: `completed`; chunked stage `complete`; `failed_sections=[]`; scalar and chunked error fields are null; `quality_passed=true`.
- No browser or additional provider call was made by the evidence collector.

## Lifecycle timestamps (UTC)

Only persisted timestamps are used. The generation row was created while awaiting approval; the first heartbeat after approval is the execution-start candidate. Missing lifecycle events are explicitly marked unavailable.

| Marker | Timestamp | Evidence |
|---|---|---|
| T0 | 2026-09-05 19:58:29.423976 | generation `created_at` |
| T1 | 2026-09-05 19:58:29.471367 | Component Lectio selected (`control.selected_at`) |
| T2 | 2026-09-05 20:13:25.497884 | first observed post-approval heartbeat; `execution_started=true` |
| T3 | 2026-09-05 20:13:48.288901 | orient `block_ready` |
| T4 | 2026-09-05 20:14:50.154402 | organise `block_ready` |
| T5 | 2026-09-05 20:15:51.589981 | guided `block_ready` |
| T6 | 2026-09-05 20:16:41.837268 | independent `block_ready` |
| T7 | 2026-09-05 20:17:17.872382 | check `block_ready` |
| T8 | 2026-09-05 20:17:18.116145 | generation `completed_at` / final heartbeat |
| T9 | 2026-09-05 20:17:21.650972 | Builder editable lesson persisted |
| T10–T12 | unavailable | no separate persisted lifecycle timestamps, request IDs, or trace events |

Derived timing: persisted-row-to-first-block `918.864925s`; execution-start-candidate-to-completion `232.618261s`; persisted-row-to-completion `1128.692169s`; persisted-row-to-Builder `1132.226996s`. `generation_time_seconds` is null.

## Ordered checkpoints and recovery

Five `generation_steps` rows were present, all `kind=lesson`, `variant_id=everyone`, `step=block_ready`:

1. `orient__hook-hero__0` — attempt 1, no recovery
2. `organise__comparison-grid__0` — attempt 1, no recovery
3. `guided__practice-stack__0` — attempt 2, `recovery=repair`
4. `independent__practice-stack__0` — attempt 2, `recovery=repair`
5. `check__quiz-check__0` — attempt 2, `recovery=repair`

## LLM call summary

Eight `llm_calls` rows were persisted; all eight have `status=succeeded`, no active calls, no failed calls, and `retryable` unset. Transport/family was `openai_compatible`, endpoint host `api.deepseek.com` (no URL path retained).

| Order | Node | Slot/model | Attempt | Latency ms |
|---:|---|---|---:|---:|
| 1–2 | `v3_section_writer` | `standard` / `deepseek-v4-pro` | 1 | 21975.4; 61366.2 |
| 3–8 | `v3_question_writer` | `fast` / `deepseek-v4-flash` | 1 | 40811.0; 20415.5; 26664.7; 23001.5; 18181.0; 17679.7 |

Total recorded call latency: `230095.1ms`; mean `28761.9ms`. No visual/media call was recorded for this run.

## Selection trace (sanitized)

The persisted `selection_trace` is an array of 5 entries. All entries are `legal=true`, `budget_pressure=null`, and have the same budget-before snapshot `{diagram-block: 3, diagram-series: 2, simulation-block: 1}`. Selected metadata (purpose text removed):

| Role | Candidate | Lane | Block/component |
|---|---|---|---|
| orient | `hook-hero` | content | `orient__hook-hero__0` / `hook-hero` |
| organise | `comparison-grid` | content | `organise__comparison-grid__0` / `comparison-grid` |
| guided | `practice-stack` | items | `guided__practice-stack__0` / `practice-stack` |
| independent | `practice-stack` | items | `independent__practice-stack__0` / `practice-stack` |
| check | `quiz-check` | items | `check__quiz-check__0` / `quiz-check` |

## Document and Builder validity

- `document_json` is present and `source_generation_id` matches the target generation.
- Canonical document top-level keys count: 12; `sections` is an array of 5; `blocks` is an object with 5 block IDs; `media` is an empty object.
- Document source is `generated`; persisted document preset is `blue-classroom`.
- Builder linkage is exact: editable lesson `14073995-f618-4bbb-885d-9f392a37eb3f`, `source_type=component_lectio`, document present, 12 document keys, 5 block keys, created/updated `2026-09-05 20:17:21.650972Z`.
- `report_json` is null and no `v3_trace_runs`/`v3_trace_events` rows are persisted for this generation; the checkpoint rows and selection trace are the authoritative available execution evidence.
- No `builder_session_id` field exists in the `editable_lessons`, `lesson_shares`, or `lesson_provenance` schema; no persisted Builder session ID is available.

## UI/status reconciliation

The database is terminal and Builder linkage is complete. A stale Units presentation can continue to show its pre-approval `Preparation / awaiting_review` heading until its preparation projection is refreshed; this does not match the target generation's persisted `status=completed` and `chunked_state.stage=complete`. Builder QA separately confirmed the linked document loaded with the expected substitution-check content and no draft-residue patterns.

## Runtime evidence

- One hidden Uvicorn worker: actual PID `6168`; one listener `127.0.0.1:8000`.
- One hidden Vite process: PID `31712`; one listener `127.0.0.1:5173`.
- `/health`, `/health/ready`, `/health/deep`: HTTP 200 / `status=ok`; readiness reported `running=0`, `pending=0` after completion.
- Runtime launcher enforced `GENERATION_PIPELINE_DEFAULT=component_lectio`, `GENERATION_MAX_CONCURRENT_PER_USER=1`, `JSON_LOGS=true`, dedicated campaign DB, and parsed/nonblank xAI/GCS runtime configuration. No provider probe was issued during this run.
- Raw local logs: `.tmp/luna_restart_20260905_230900/backend.stderr.log` and `.tmp/luna_restart_20260905_230900/frontend.stdout.log`.

