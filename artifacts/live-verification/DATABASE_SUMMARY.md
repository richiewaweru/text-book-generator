# Component Lectio Database Summary

For each generation capture sanitized `generations`, ordered `generation_steps`, relevant `llm_calls`, selection trace, retries/repairs, terminal state, and document presence. Never store credentials, complete provider prompts/responses, or learner-sensitive content.

## Run 3 — PASS

- Generation `7623d9cc-378b-4a45-a649-31517bd5b240` completed on SHA `9871fcaa`; Builder `14073995-f618-4bbb-885d-9f392a37eb3f` persisted with `source_type=component_lectio` and matching `source_generation_id`.
- `generations`: `status=completed`, `stage=complete`, pipeline marker `component_lectio`, `quality_passed=true`, valid five-section document, no final error, and no failed blocks. Ordered checkpoints and selection trace were retained; three block-scoped repairs are recorded.
- Eight successful DeepSeek text calls were persisted; no visual calls and no transport failures. Duplicate `awaiting_review` row `303e332e` is orphaned and made zero provider calls; it is excluded from the authoritative run.
- Browser/DB reconciliation confirmed `blue-classroom`, four equation forms and substitution checking, no provider drafting residue, preserved currency, and exact Builder linkage. This is local run 3 of 12 and does not establish four-consecutive local or hosted stability.

## Run 2 — FAIL_P1_CONTENT_QUALITY

- Generation `618e4647-dcc9-4b5d-9f8a-5da1b0dda1e6` completed on verified SHA `408eac6` at provider-capacity position `2 of 12`; Builder `b2d595f8-49bc-454e-8c31-973c2e249ad4` persisted with `source_type=component_lectio` and matching `source_generation_id`.
- `generations`: Mathematics; context is the approved path lesson; requested/resolved template `guided-concept-path`; requested/resolved preset `v3-studio`; status `completed`; stage `complete`; pipeline marker `component_lectio`; five sections; `failed_sections=[]`; no persisted generation error; `quality_passed=true` (structural/contract result, not semantic content approval).
- Source checkpoint: approved Grade 7 unit destination `By the end, students can solve and check one-step linear equations`; path lesson `ce44273a-995b-4583-8d6a-4a1a67dd0b85`, path version `25397571-8137-4eca-91c8-1925fe73a0fe` version 1/revision 4, `source=path_planner`, lesson revision 2. Seven ordered `block_ready` checkpoints use plan hash `ae1f7c20f7e8040ffe7459e9dcd56396fcf3322650bc9eaba8a4de3fcc1d35b8`, revision 1; independent work order is `wo::independent__practice-stack__0`.
- Exact persisted independent p1: `Solve 500 - x = 375 for x, where x is the unknown withdrawal that reduces a $500 balance to $375.` → answer `125`; empty hints; rationale adds 375 to both sides. The shortened observed form `...reduces a 375.` does not occur in the generation document, independent checkpoint payload, or Builder document.
- Exact persisted independent p2: `Solve x + 45 = 200 for x, where x is the unknown starting balance before a $45 withdrawal leaves $155? Wait, adjust: actually solve x + 45 = 200 representing balance after adding back or similar withdrawal verification.` → answer `155`; empty hints; rationale subtracts 45 from both sides. The self-edit/contradictory framing occurs once in each of those three persisted surfaces and is raw provider corruption.
- Objective coverage spans all four required forms (`x+a=b`, `x-a=b`, `ax=b`, `x/a=b`) and substitution check; only p2 fails semantic content quality. Classification is `FAIL_P1_CONTENT_QUALITY`, excluded from pass and latency statistics; no Legacy planning started.
- Checkpoint/recovery: independent attempt 1/no recovery; guided and check attempt 2/`repair`; remaining five blocks attempt 1/no recovery. All final checkpoints are `block_ready`; no explicit QC report or v3 trace rows are persisted, so the malformed content escaped the structural gate.
- Provider/model/transport: nine successful calls, four `v3_section_writer` standard and five `v3_question_writer` fast, all `openai_compatible`/`grok-4.3`/`api.x.ai`; no transport retries. Lifecycle timestamps and derived timings are documented in `RUN02_CONTENT_QUALITY.md`.

## Preflight migration validation

- Dedicated database: `textbook_agent_component_lectio_campaign`
- Engine: local PostgreSQL 16 container
- Sequence: fresh upgrade → `20260904_0033`; downgrade → `20260806_0032`; upgrade → `20260904_0033`
- Historical generation-step uniqueness constraint present counts: `0 → 1 → 0`
- Result: PASS

## L01 Units → Builder reconciliation — INVALID_SCOPE_SELECTION

- Read-only Builder GET confirmed an `editable_lessons` row now exists: `id=6ebbcec4-fd94-494b-b163-ec4322ae2c3a`, title `Identify the operation`, `source_type=component_lectio`.
- `source_generation_id=24586f47-c8bd-415a-9a43-cc77401a299b`, matching the expected completed L01 generation; document is present with five sections and five Component Lectio blocks.
- This updates the earlier backend-only note that the row was absent; no database write was performed by this verification. Sanitized UI/network details are in `L01_UNITS_BUILDER_UI.md`.
- Classification: `INVALID_SCOPE_SELECTION`; provider-capacity generation `1 of 12`, old SHA `63390e64`. Selected lesson 0 explicitly excludes solving, so content did not match the campaign scenario. Builder linkage/UI interaction passed; the `default` preset warning was confirmed and fixed separately.
- Follow-up objective/preset trace is recorded in `L01_OBJECTIVE_PRESET_TRACE.md`. This generation is excluded from latency/pass statistics; no L02 was started.

Startup readiness confirmed PostgreSQL connectivity (`/health/ready` dependency `postgres=status=ok`) against the dedicated `textbook_agent_component_lectio_campaign` database. Image readiness passed in the prior authorized probe (`grok_imagine_only=ok`, `v3_gcs_upload_only=ok`, HTTP 200, 9.637s). Pre-legacy baseline on fix SHA `738dde4a8c0596b6cb29f6c14fd8996974b7dd98` confirmed zero `generations`, zero `generation_steps`, and zero `llm_calls`; zero paid lesson runs. Backend validation result: `692 passed`, 1 known warning. No lesson generation was started at that baseline.

Final aggregate gate on the same SHA exited `0`; backend Ruff, frontend check/build, and tooling pytest passed, with only the documented warnings. Isolated temporary validation state was cleaned.

## Campaign gate — PAUSED_P0_UNITS_CUTOVER

- Real-generation count: `0`; CL-LOCAL-001 is not counted as executed.
- P0 blocker: `/units/[id]` preparation redirects to `/studio` (`frontend/src/routes/units/[id]/+page.svelte:322-326`). The bridge creates the generation and invokes path initialization (`backend/src/planning/bridge.py:577-648`), whose structural/chunked state has no `control.pipeline` marker (`backend/src/generation/path_preparation.py:46-114`); the resolver maps a missing marker to `v3_studio` (`backend/src/generation/pipeline_dispatch.py:70-91`). Studio approval is the only approval path (`frontend/src/routes/studio/+page.svelte:725`), and the Component Lectio branch requires the persisted marker (`backend/src/generation/v3_studio/router.py:2591-2603`).
- Campaign status: `PAUSED_P0_UNITS_CUTOVER`; no source, browser, provider, or database mutation is authorized until this scope/marker gap is corrected.

## Prior `/studio` pre-generation attempt — INVALID_SCOPE_LEGACY

- This attempt is excluded from CL-LOCAL-001 and from the real-generation count. It is retained solely as paid pre-generation legacy evidence.
- T0 baseline (UTC): `2026-09-05T09:56:19.979Z`; SHA `738dde4a8c0596b6cb29f6c14fd8996974b7dd98`.
- Dedicated database `textbook_agent_component_lectio_campaign` is at migration `20260904_0033`.
- Sanitized terminal counts: `generations=0`, `generation_steps=0`, `learning_packs=0`, `llm_calls=7`, `v3_trace_runs=0`, `v3_trace_events=0`, `editable_lessons=0`, `lesson_provenance=0`.
- No counted concept-plan generation row, generation ID, ordered generation step, trace run, document, or Builder record exists. Seven paid pre-generation telemetry calls were persisted; no manual retry or approval occurred.
- Call sequence: `v3_narrow` / `deepseek-v4-flash` / `api.deepseek.com` attempt 1 `failed`, created `2026-09-05T10:00:12.973483Z`, latency `30020.690ms`; attempt 2 `succeeded`, created `2026-09-05T10:00:27.738807Z`, latency `14198.003ms`, 389 input / 1671 output / 1462 thinking tokens.
- Call sequence: `v3_propose_intent` / `deepseek-v4-pro` / `api.deepseek.com` attempt 1 `failed`, created `2026-09-05T10:01:20.372967Z`, latency `25007.517ms`; attempt 2 `succeeded`, created `2026-09-05T10:01:33.136411Z`, latency `12461.925ms`, 521 input / 730 output / 548 thinking tokens.
- Call sequence: `v3_signal_extractor` / `deepseek-v4-flash` / `api.deepseek.com` attempts 1–3 `failed`, created `2026-09-05T10:02:30.808699Z`, `2026-09-05T10:03:01.325038Z`, and `2026-09-05T10:03:32.390973Z`, latencies `29998.542ms`, `29998.689ms`, and `29987.407ms`.
- Persisted `started_at`, `completed_at`, retryable, and error fields were null; no raw provider error was recorded. This is classified `INVALID_SCOPE_LEGACY` because the attempt used the `/studio` pre-generation path before the unit cutover scope was resolved; the signal extractor still exhausted its three attempts and the UI received HTTP 500 before generation creation.
- No authenticated user identifier was needed for this evidence and none is recorded.
