# Component Lectio Campaign Environment

Populate values before each environment sequence. Never record tokens, passwords, connection strings, OAuth identifiers, or service-account JSON.

## Local

- Commit SHA: `738dde4a8c0596b6cb29f6c14fd8996974b7dd98` (local HMR verification)
- Frontend: native development server
- Backend: one native Uvicorn process, one worker
- Database: dedicated local PostgreSQL campaign database
- Pipeline: `component_lectio` (must be explicit)
- Admission concurrency: `1`
- Structured logs: enabled
- Providers/models: xAI image route configured as `xai` / `grok-imagine-image`; secret value not recorded
- Migration revision: `20260904_0033` on PostgreSQL 16; upgrade/downgrade/upgrade verified
- Readiness: `/health`, `/health/ready`, and `/health/deep` returned HTTP 200 with `status=ok` on the HMR runtime. The previously authorized image probe remains the final provider evidence (`grok_imagine_only=ok`, `v3_gcs_upload_only=ok`); no new probe was issued. Servers remain running, but the campaign is paused at the P0 units cutover gate.

- First-load Units defect: fixed in `738dde4a8c0596b6cb29f6c14fd8996974b7dd98`; capability hydration now reacts when onboarding establishes the authenticated user, so Units does not require a full reload.

- Final aggregate gate on `738dde4a8c0596b6cb29f6c14fd8996974b7dd98`: PASS, exit `0`; isolated temporary validation state was cleaned.

- Campaign gate: `PAUSED_P0_UNITS_CUTOVER`; real-generation count `0`. Unit preparation redirects to `/studio` (`frontend/src/routes/units/[id]/+page.svelte:322-326`), and the path-preparation state omits `chunked_state_json.control.pipeline` (`backend/src/generation/path_preparation.py:46-114`), causing missing-marker resolution to `v3_studio` (`backend/src/generation/pipeline_dispatch.py:70-91`).
- Prior `/studio` pre-generation attempt is retained separately as `INVALID_SCOPE_LEGACY`; its seven paid pre-generation calls do not count toward CL-LOCAL-001.

## L01 Units reconciliation — INVALID_SCOPE_SELECTION

- Provider-capacity generation `1 of 12`: generation `24586f47-c8bd-415a-9a43-cc77401a299b` reached `completed`; chunked stage was `complete`, persisted pipeline marker was `component_lectio`, and the document was present with expected LessonDocument top-level contract keys.
- Selected lesson was path position `0`, explicitly excluded `solving the equation`, and therefore did not match the campaign scenario. Recorded runtime was approximately 122.694 seconds from `2026-09-05 14:42:25.673604` to `2026-09-05 14:44:28.367813`; this diagnostic duration is excluded from campaign latency/pass statistics. Five ordered `block_ready` steps were persisted; the guided block recorded one repair attempt (`attempt=2`, `recovery=repair`); other blocks recorded attempt 1.
- Sanitized LLM evidence: 6 successful `v3_execution` calls using `openai_compatible` / `grok-4.3` through xAI transport (2 section-writer, 4 question-writer). Both `chunked_state_json.selection_trace` and `chunked_state_json.canonical_plan.selection_trace` were present as arrays of length 5; entries exposed only the keys `role`, `legal`, `intent`, `selected`, `section_id`, `budget_before`, `candidate_set`, and `budget_pressure`.
- Builder linkage/UI interaction passed separately; the `default` preset warning was confirmed and fixed separately. No L02 was started, and this generation is not a campaign PASS or PASS_WITH_RECOVERY.

## Hosted canary

- Commit SHA: pending
- Frontend: Vercel canary
- Backend: Railway canary, one replica, one worker
- Database: controlled hosted/staging PostgreSQL
- Pipeline: `component_lectio` (must be explicit)
- Autoscaling/parallel workers: disabled for the campaign
- Migration revision: pending
- Deployment, readiness, logs, and DB access: pending
