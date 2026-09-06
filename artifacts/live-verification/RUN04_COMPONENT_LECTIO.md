# Run 4 — Component Lectio visual-QC reconciliation
Sanitized local campaign evidence for generation `7f2ff0ef-2a00-4dc8-9dd7-8ad7570a08df`. Prompts, learner identifiers, credentials, raw provider errors, and lesson/document text are omitted. Browser observations below are recorded as operator-supplied QA; this agent performed DB/log inspection only.

## Scope and disposition

- Verified source SHA: `b41a6d1c13856cc09b4f974455532bdffc638ab8`.
- Database: `textbook_agent_component_lectio_campaign` (PostgreSQL 16), migration `20260905_0034`.
- Science unit: `2c680d64-e23c-4fbf-bb7f-bc5f4016a4d0`; the displayed ninth lesson is persisted at zero-based path position `8`, path lesson `12fae584-8b5d-4b5d-bf97-5f2abfd672c2`.
- Persisted control marker: `pipeline=component_lectio`, `pipeline_version=1`.
- Requested/resolved template: `guided-concept-path`; requested/resolved preset: `v3-studio`; mode `v3`; section count `4`.
- Terminal scalar/chunked state: `status=completed`, `stage=complete`, `quality_passed=true`, `failed_sections=[]`, no persisted error fields, and `document_json` present.
- Disposition: `FAIL_P1_VISUAL_QC`. The visual-QC call failed, the diagram block nevertheless reached `block_ready`, and the resulting Builder diagram was observed broken with repeated prompt text. Exclude from pass and latency statistics.

## Lifecycle timestamps (UTC)

The generation row was created while awaiting approval. The first observed heartbeat after approval is the execution-start candidate.

| Marker | Timestamp | Evidence |
|---|---|---|
| T0 | 2026-09-05 20:57:34.141518 | generation `created_at` |
| T1 | 2026-09-05 20:57:34.517851 | Component Lectio selected (`control.selected_at`) |
| T2 | 2026-09-05 23:54:57.423035 | first observed execution heartbeat; `execution_started=true` |
| T3 | 2026-09-05 23:55:12.958354 | orient `block_ready` |
| T4 | 2026-09-05 23:55:37.792756 | explain prose `block_ready` |
| T5 | 2026-09-05 23:55:44.527436 | explain diagram `block_ready` |
| T6 | 2026-09-05 23:55:52.495417 | explain key-fact `block_ready` |
| T7 | 2026-09-05 23:56:19.526590 | contrast `block_ready` |
| T8 | 2026-09-05 23:56:35.390244 | check `block_ready`, attempt 2/recovery repair |
| T9 | 2026-09-05 23:56:35.436943 | generation `completed_at` / final heartbeat |
| T10 | 2026-09-05 23:56:37.678044 | Builder editable lesson persisted |
| T11–T12 | unavailable | no separate persisted lifecycle timestamps or trace events |

Derived timing: persisted-row-to-first-block `10658.816836s`; execution-start-candidate-to-completion `98.013908s`; persisted-row-to-completion `10741.295425s`; persisted-row-to-Builder `10743.536526s`. Stored `generation_time_seconds` is null.

## Ordered checkpoints and recovery

Six `generation_steps` rows were present, all `kind=lesson`, `variant_id=everyone`, `step=block_ready`:

1. `orient__hook-hero__0` — attempt 1, no recovery
2. `explain__explanation-block__0` — attempt 1, no recovery
3. `explain__diagram-block__1` — attempt 1, no recovery
4. `explain__key-fact__2` — attempt 1, no recovery
5. `contrast__comparison-grid__0` — attempt 1, no recovery
6. `check__quiz-check__0` — attempt 2, `recovery=repair`

## Provider/model/transport evidence

Seven `llm_calls` rows were persisted. Six succeeded and one failed; no call was active at terminal state.

| Calls | Node | Family / model | Endpoint | Result | Latency ms |
|---:|---|---|---|---|---:|
| 4 | `v3_section_writer` | `openai_compatible` / `deepseek-v4-pro` | `api.deepseek.com` | succeeded | 15018.7; 24690.0; 7834.1; 26921.7 |
| 2 | `v3_question_writer` | `openai_compatible` / `deepseek-v4-flash` | `api.deepseek.com` | succeeded | 7294.8; 8374.7 |
| 1 | `v3_visual_qc` | `anthropic` / `claude-haiku-4-5-20251001` | endpoint host not persisted | failed | 807.7 |

The visual-QC failure is sanitized as a provider billing/credit rejection (HTTP 400); raw error text and request identifiers are not retained here. No separate successful image-generation call was persisted. Total recorded call latency was `90941.7ms` (mean `12991.7ms`); no transport retry was recorded.

## Visual block and media validity

- The selector legally selected `diagram-block` in the `explain` role on the visual lane.
- The persisted diagram block has `component_id=diagram-block`, content keys `{alt_text, caption, image_url}`, and a nonblank `image_url` pointing to an `https://api.x.ai/...` API-shaped path. It is not a GCS URL and no SVG/HTML source field exists.
- `document_json.media` is an object with zero entries; chunked lesson-document media is also an empty object.
- `alt_text` and `caption` are identical and match the diagram prompt-echo marker. No warning/flag metadata or failed-section marker was persisted.
- Operator-supplied Builder QA observed a broken-image icon and repeated prompt text in the diagram block, despite the overall generation and Builder opening as complete.

This violates the readiness contract: a visual provider/QC failure and unusable diagram must not be represented as a successful complete lesson. The scalar `quality_passed=true` is structural status only and does not override the visual failure.

## Selection trace (sanitized)

The persisted `selection_trace` is an array of 4 entries. All entries are `legal=true`, `budget_pressure=null`, and share budget-before `{diagram-block: 3, diagram-series: 2, simulation-block: 1}`. Purpose text was removed.

| Role | Candidates | Selected metadata |
|---|---|---|
| orient | `hook-hero` | content / `orient__hook-hero__0` / `hook-hero` |
| explain | `explanation-block`, `diagram-block`, `key-fact` | visual / `explain__diagram-block__1` / `diagram-block`; content / `explain__explanation-block__0` / `explanation-block`; content / `explain__key-fact__2` / `key-fact` |
| contrast | `comparison-grid` | content / `contrast__comparison-grid__0` / `comparison-grid` |
| check | `quiz-check` | items / `check__quiz-check__0` / `quiz-check` |

## Builder/linkage and UI notes

- Builder editable lesson `bced2938-e7d0-41bf-bacf-47bcc1e23911` persisted with `source_type=component_lectio`, matching `source_generation_id`, document present, 6 block keys, and zero media entries.
- No `builder_session_id` field is persisted in the relevant Builder schema.
- The review UI showed raw prerequisite UUIDs; this is recorded as a separate P2 presentation issue and is not the run disposition.

## Runtime and campaign totals

- One hidden Uvicorn worker: actual PID `25172`; one listener `127.0.0.1:8000`.
- One hidden Vite process: PID `34664`; one listener `127.0.0.1:5173`.
- `/health`, `/health/ready`, `/health/deep`: HTTP 200 / `status=ok`; no running or pending generation remained after completion.
- Campaign totals after the run: `4 completed`, `1 awaiting_review`, `0 running/pending`, `5 total`.
- Raw local logs: `.tmp/luna_restart_20260905_234909/backend.stderr.log` and `.tmp/luna_restart_20260905_234909/frontend.stdout.log`.
