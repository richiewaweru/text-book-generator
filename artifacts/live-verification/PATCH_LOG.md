# Component Lectio Stabilization Patch Log

Do not blend evidence across code SHAs. For every patch record the originating generation when applicable, evidence, root cause, smallest fix, regression test, validation, commit, and remaining risk.

## Pre-live baseline

- Starting SHA: `8509233`
- Final-contract baseline: `23 passed, 1 warning` using an isolated pytest temporary directory
- Shared default pytest DB attempt: blocked by an existing Windows file lock; no tracked files changed
- Required pre-live patches: implemented in the working tree; commits pending full static gates

## Pre-live regression evidence

- Focused unit/integration set: `51 passed, 1 warning`.
- Final-contract, pre-live, cutover, E2E, and lifecycle gates: `75 passed, 1 warning`.
- Ruff check over all changed Python files: passed.
- PostgreSQL 16 migration on `textbook_agent_component_lectio_campaign`: fresh upgrade to `20260904_0033`, downgrade to `20260806_0032`, and re-upgrade to `20260904_0033` all passed. Constraint counts were `0 → 1 → 0`.
- The warning is the pre-existing Pydantic field-shadow warning in `contracts/generation_manifest.py`.
- Frontend `npm run check` passed with 0 errors and 2 pre-existing unused CSS warnings.
- Frontend `npm run build` passed with existing optional-dependency and chunk-size warnings.

## Independent audit follow-up

- P1 lifecycle audit found a race in terminal lifecycle persistence: concurrent/repeated completion and failure paths could overwrite terminal state inconsistently. The smallest fix makes terminal state updates deterministic and keeps checkpoint recovery append-only; lifecycle regression tests cover success, failure, repeated checkpoints, and restart reconstruction.
- P2 test improvements added focused lifecycle/contract coverage; sanitizer improvements constrain campaign evidence to allowlisted metadata and exclude prompts, lesson/document content, user identifiers, credentials, and raw provider errors.
- Focused audit result: `46 passed`; targeted Ruff check passed.
- The first full validation attempt found 10 pre-existing Ruff failures plus one stale Stage 2 test. Those remain under minimal-gate repair and are not represented as campaign passes.

## Final static gates

- Architecture check: PASS.
- Isolated aggregate `validate_repo` completed with exit code `0`: backend Ruff PASS; backend pytest `690 passed, 1 known warning`; frontend check `0 errors, 2 warnings`; frontend build PASS; tooling pytest `11 passed`.
- The earlier shared-temp database-lock cascade was invalidated by the successful isolated validation pass; it is not treated as a repository or campaign failure.

## Local campaign startup preflight

- Approved SHA: `a9076fd21294472ddead0ac7120a84ff0e998de7`.
- Dedicated PostgreSQL database: `textbook_agent_component_lectio_campaign`; backend configured with `GENERATION_PIPELINE_DEFAULT=component_lectio`, `GENERATION_MAX_CONCURRENT_PER_USER=1`, `JSON_LOGS=true`, and one Uvicorn worker.
- Backend/frontend remained running on `127.0.0.1:8000` and `127.0.0.1:5173`; raw logs are in a unique system-temp campaign directory (not tracked). PIDs are intentionally omitted from committed evidence.
- `GET /health`, `GET /health/ready`, and `GET /health/deep` each returned HTTP 200 with `status=ok`; readiness reported PostgreSQL, event bus, Playwright, and PDF temp directory healthy.
- The authorized `POST /health/image/probe` was attempted exactly once. The shell produced no capturable response body or status, so provider/model/image-store readiness is recorded as unresolved; no generation was started.
- Controlled replacement `POST /health/image/probe` used a 240-second client timeout and returned HTTP `503` in `5.665s`, with `status=unavailable`. Sanitized dependencies: `grok_imagine_only=ok` (xAI / `grok-imagine-image`), `v3_gcs_upload_only=unreachable`; probe bytes were present but no image content was retained. Core `/health` remained HTTP 200 afterward.
- Campaign stop condition: image-store readiness is a P1 blocker (`v3_gcs_upload_only=unreachable`); do not start lesson generation until storage readiness is repaired and a separately authorized probe passes.

## Image-store P1 diagnosis

- Saved probe evidence is conclusive: `grok_imagine_only=ok`, while the GCS leg was `unreachable` with the sanitized failure class `GCS upload returned no URL`. This is a disabled-store/configuration failure, not evidence of provider failure, DNS failure, or a permissions denial.
- Root `.env` contains nonblank values for `GCS_BUCKET_NAME`, `GCS_SERVICE_ACCOUNT_JSON`, and `GCS_IMAGE_BASE_URL`; `backend/.env` declares those same names but blank. The transient launcher injected root values only when names were absent, so blank backend entries won precedence and left the store disabled. No credential file path is configured (`GOOGLE_APPLICATION_CREDENTIALS` absent); credentials are intended as inline service-account JSON.
- Smallest remediation: inject root GCS values when backend values are absent *or blank* (process environment only), or configure equivalent nonblank backend runtime variables without committing secrets. Then restart and run one newly authorized readiness probe; do not reuse this failed probe as proof.

## P1 correction and post-fix gates

- The P1 correction adds staging/production-like image-store consistency so the readiness path exercises the configured GCS store rather than silently using a disabled local/no-op store. A mocked HTTP 503 regression test covers the failed readiness response path.
- Focused post-fix result: `38 passed, 1 known warning`; Ruff, architecture, frontend, and tooling checks passed.
- The aggregate backend result is invalidated by the known SQLite file-lock failure; a standalone full backend rerun remains pending. Do not treat the aggregate as final campaign validation.

## Known P2 observations (not fixed)

- Raw and typed GCS configuration remain split across configuration surfaces.
- Post-upload URL behavior remains ambiguous between configured base URLs and signed URLs.
- Negative readiness results remain subject to cache TTL behavior.

## Final-SHA local readiness attempt

- Approved SHA: `cda9d6f31b3e3a5b279abf917bf7599a1e4199af`; dedicated PostgreSQL migration was current at `20260904_0033`.
- One backend (`--workers 1`, admission concurrency `1`, explicit `component_lectio`, JSON logs) and one frontend were started with process-only secret/config injection. Health, readiness, and deep-health endpoints each returned HTTP 200 with `status=ok`.
- Exactly one controlled replacement image probe was issued with a 240-second client timeout. Sanitized result: HTTP 503, `status=unavailable`, latency `8.867s`; `grok_imagine_only=ok` (xAI / `grok-imagine-image`) and `v3_gcs_upload_only=unreachable`.
- No lesson generation was run. The backend and frontend were stopped immediately after the P1 result; local readiness remains unchecked. Raw logs remain only in the unique system-temp campaign directory and are not committed.
- The launcher correction ensured root values filled backend variables when missing *or blank*, and runtime nonblank checks passed. Since GCS still failed, the final storage cause is not yet narrowed to auth/permission, bucket/configuration, network, or code behavior; do not claim campaign readiness until a read-only diagnosis and separately authorized probe succeed.

## Final-SHA operational retry

- On `cda9d6f31b3e3a5b279abf917bf7599a1e4199af`, the launcher was corrected so a child Python process reads root dotenv values, validates the credential JSON, and assigns the required secrets/configuration directly to its own environment before importing Uvicorn. No environment file was edited.
- Migration `20260904_0033` was current. One backend worker and one frontend were running with explicit `component_lectio`, admission concurrency `1`, and JSON logs. `/health`, `/health/ready`, and `/health/deep` each returned HTTP 200 with `status=ok`.
- Exactly one actual POST image probe was issued with a 240-second timeout and returned HTTP 200 / `status=ok` in `9.637s`; sanitized dependencies were `grok_imagine_only=ok` and `v3_gcs_upload_only=ok`, with probe bytes present. Core health remained 200 afterward.
- Backend validation result recorded for this campaign: `692 passed`, 1 known warning. No lesson generation was run; servers remain running for browser campaign.

## Final-SHA GCS diagnosis (read-only)

- Saved response confirms `probe_image_bytes=113015`; xAI/model completed successfully, and the GCS leg failed at `stage=gcs_upload` with a sanitized `JSONDecodeError` during store construction. This is before bucket permission, network, upload, or URL generation.
- Root `.env` credential JSON parses successfully, service-account credential construction succeeds, and one metadata-only bucket existence check returned `exists`; no object was uploaded or deleted. Required root GCS values are nonblank. Therefore the final failure is launch-time environment serialization/injection corruption of `GCS_SERVICE_ACCOUNT_JSON`, not GCS auth, permission, bucket existence, network, upload, or URL generation.
- `GCS_IMAGE_BASE_URL` was nonblank in the source and launcher boolean checks, but the constructor failed before assigning/using it; its process-side exact value was not exposed or independently proven. Smallest next action: fix the launcher to transfer the parsed credential JSON losslessly (e.g. process environment API or a protected temporary environment mechanism), assert JSON parsing in the child before startup, then obtain separate authorization for one replacement probe.

## First-load Units defect and fix

- Confirmed defect: after onboarding, the root layout could finish auth hydration with no capability request for the newly authenticated user. Because Units navigation and `/units` access depend on `xploreV2`, the first `/lessons` render could omit Units or redirect until a full reload retried capability loading.
- Fix: `738dde4a8c0596b6cb29f6c14fd8996974b7dd98` (`fix(lectio): refresh capabilities after onboarding`) makes capability hydration user-reactive and adds focused regression coverage for onboarding authentication and capability failure behavior.
- Focused frontend tests, `npm run check`, and `npm run build` passed; build retained the existing optional-dependency/chunk-size warnings. No new provider call or image probe was made during this verification.
- Runtime verification on the fix SHA: one backend worker and one frontend listener; health/ready/deep all HTTP 200/`ok`. Dedicated campaign database remains zero `generations`, zero `generation_steps`, and zero `llm_calls`; zero paid lesson runs.

## Final aggregate gate

- SHA `738dde4a8c0596b6cb29f6c14fd8996974b7dd98`: isolated aggregate validation exited `0`.
- Backend Ruff: PASS. Backend pytest: `692 passed`, 1 known Pydantic warning. Frontend check: `0 errors`, 2 known unused-CSS warnings. Frontend build: PASS with known optional-dependency/chunk-size warnings. Tooling pytest: `11 passed`.
- Isolated temporary validation state was cleaned. No provider calls or paid lesson runs were part of this gate.

## Prior `/studio` pre-generation attempt — INVALID_SCOPE_LEGACY

- The prior `/studio` pre-generation attempt is reclassified `INVALID_SCOPE_LEGACY` and explicitly excluded from `CL-LOCAL-001` and the real-generation count. IAB cursor `639` showed successful narrow (`645/650/652`, HTTP 200) and propose-intent (`655/658/660`, HTTP 200), followed by signals (`663/668/670`, HTTP 500 `text/plain`). The UI reset with `Internal Server Error`; no manual retry or approval occurred.
- Reconciled dedicated DB state: `generations=0`, `generation_steps=0`, `learning_packs=0`, `v3_trace_runs=0`, `v3_trace_events=0`, `llm_calls=7`. No counted concept-plan generation row was created, but seven paid pre-generation calls occurred.
- Narrow succeeded on attempt 2 after one failure; propose-intent succeeded on attempt 2 after one failure; signal extraction failed on attempts 1–3 with approximately 30-second latencies. No document, visual asset, PDF, or Builder state exists for this stopped run.
- Legacy attempt root cause: provider-backed signal-extraction failure exhausted retries before generation creation. Raw prompts, responses, user identifiers, credentials, and raw provider errors were not recorded.

## Campaign gate — PAUSED_P0_UNITS_CUTOVER

- Real-generation count is `0`; CL-LOCAL-001 was not run and must not inherit the prior legacy attempt's paid-call evidence.
- P0 blocker: the unit “Make the lesson” action redirects to `/studio` (`frontend/src/routes/units/[id]/+page.svelte:322-326`), while the bridge creates the generation and path preparation initializes chunked state without `chunked_state_json.control.pipeline` (`backend/src/planning/bridge.py:577-648`; `backend/src/generation/path_preparation.py:46-114`). The resolver maps an absent marker to `v3_studio` (`backend/src/generation/pipeline_dispatch.py:70-91`), and Studio's approval/execution selects Component Lectio only when the persisted marker is present (`frontend/src/routes/studio/+page.svelte:725`; `backend/src/generation/v3_studio/router.py:2591-2603`).
- Campaign status: `PAUSED_P0_UNITS_CUTOVER`. No new generation, retry, approval, browser action, provider call, or source edit was performed for this evidence update.

## L01 Units reconciliation — INVALID_SCOPE_SELECTION

- Provider-capacity generation `1 of 12` on old SHA `63390e64`; read-only reconciliation of generation `24586f47-c8bd-415a-9a43-cc77401a299b`: terminal `completed`, chunked stage `complete`, pipeline `component_lectio`, document present, five ordered block checkpoints, and no persisted error.
- Selected path lesson 0 explicitly excludes solving; generated content therefore did not match the campaign scenario and is classified `INVALID_SCOPE_SELECTION`, not `PASS`, `PASS_WITH_RECOVERY`, or a P1 product failure. Duration was approximately `122.694s` for diagnostics only and is excluded from campaign latency/pass statistics. Four blocks used attempt 1 and `guided__practice-stack__0` used attempt 2 with `recovery=repair`. Sanitized execution calls: 6 successful xAI `grok-4.3` calls over `openai_compatible` transport (2 section writer, 4 question writer).
- Both `chunked_state_json.selection_trace` and `chunked_state_json.canonical_plan.selection_trace` were present as arrays of length 5. Sanitized entry keys were `role`, `legal`, `intent`, `selected`, `section_id`, `budget_before`, `candidate_set`, and `budget_pressure`; no raw selection payload was retained. Builder linkage/UI interaction passed; the `default` preset warning was confirmed and fixed separately. No L02 was started.

## Run 3 — corrected Units hydration/review duplicate — PASS

- Authoritative local generation `7623d9cc-378b-4a45-a649-31517bd5b240` ran on exact SHA `9871fcaa09ed253069547bb08854bb17f5f44466` (`9871fca`), after the Units hydration fix commit `9871fca`. It completed with truthful `status=completed` / `stage=complete`, valid document, and exact Builder linkage.
- Duplicate `awaiting_review` row `303e332e` was diagnosed as orphaned and made zero provider calls. It is excluded from the authoritative run; no rerun was triggered from it.
- Authoritative execution used eight successful DeepSeek text calls and no visual calls. Three block-scoped repairs were captured. Browser evidence confirmed `blue-classroom`, all four equation forms plus substitution, no drafting residue, and preserved currency rendering.
- Classification: `PASS`, local run 3 of 12. This does not satisfy the four-consecutive local gate; no hosted canary or Legacy deletion has begun. Legacy removal remains a future evidence-based plan, not an action in this run.

## Run 4 — visual-QC failure and corrective sequence

- Run 4 generation `7f2ff0ef-2a00-4dc8-9dd7-8ad7570a08df` was verified on exact SHA `b41a6d1c13856cc09b4f974455532bdffc638ab8`. It completed with `status=completed`, `stage=complete`, `quality_passed=true`, `failed_sections=[]`, and a persisted Builder document, but the required `diagram-block` had a broken xAI-shaped image URL, empty media, and prompt-echo caption/alt text. Classification is `FAIL_P1_VISUAL_QC`; exclude it from pass and latency statistics. Detailed sanitized evidence is in `RUN04_COMPONENT_LECTIO.md`.
- Corrective commits, in order: `04a2412` (`fix(lectio): fail closed when visual quality is unavailable`), `9e1dba8` (`fix(lectio): separate image storage from provider endpoints`), and `c3a2632` (`fix(lectio): flag visuals when quality service is unavailable`). The final user-directed temporary policy is: QC-unavailable images with usable bytes are retained as `flagged_quality`; explicit QC rejection remains an omission/block; missing media/source remains an assembly blocker.
- Current focused validation on `c3a2632` covered the affected visual, Component Lectio contract, and image-settings suites: `86 passed, 1 warning` in `25.85s`. The warning is the known Pydantic field-shadow warning in `contracts/generation_manifest.py`.
- The last clean isolated repository aggregate remains the prior exact-SHA result on `738dde4a`: backend pytest `692 passed, 1 known warning`; frontend check `0 errors, 2 warnings`; frontend build PASS with known optional-dependency/chunk-size warnings; tooling pytest `11 passed`; architecture PASS. A fresh all-scope run after the three corrective commits has not produced a final total: the shared-temp attempt was blocked by a Windows SQLite lock and the subsequent isolated run was interrupted during legacy v3 failures. Do not label the current aggregate green.
- PostgreSQL 16 migration roundtrip evidence: dedicated campaign DB fresh upgrade to `20260904_0033`, downgrade to `20260806_0032`, and re-upgrade to `20260904_0033` passed, with uniqueness counts `0 → 1 → 0`. Run 4 observed the DB at current head `20260905_0034`; no separate `0034` downgrade/upgrade roundtrip is recorded.
- Current repository HEAD is exact SHA `c3a2632785dcda8a04cb2eb2880e8ce35ccea02d`. Backend/frontend processes were restarted after that commit (latest restart logs begin `2026-09-06 04:09`), but the persisted process record does not include a commit stamp and no post-restart replacement generation/readiness proof is recorded. Exact-SHA restart/readiness verification remains pending; no new paid lesson run is authorized by this entry.
