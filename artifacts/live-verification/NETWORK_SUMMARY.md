# Component Lectio Network Summary

For each run record sanitized URL path, method, status, start/end time, generation ID, polling cadence, long/failed requests, pipeline/stage fields, document fetches, visual asset results, and PDF requests. Save a sanitized HAR when available.

## Run 3 — PASS

- Verified SHA: `9871fcaa09ed253069547bb08854bb17f5f44466`; authoritative generation `7623d9cc-378b-4a45-a649-31517bd5b240`; Builder `14073995-f618-4bbb-885d-9f392a37eb3f`.
- Units-native flow remained on `/units` and `/builder`; no `/studio` URL or hidden fallback was observed. Duplicate `awaiting_review` row `303e332e` was orphaned and made zero provider calls.
- Reconciled terminal API/DB state: `component_lectio`, `stage=complete`, `status=completed`, valid document, matching Builder source generation, and no failed blocks. Browser verification confirmed `blue-classroom`, four equation forms plus substitution, no residue, and currency preserved.
- Authoritative execution recorded eight successful DeepSeek text calls and no visual/media calls. No PDF or save/reload check was designated for this Math run. Detailed timing evidence is in `RUN03_COMPONENT_LECTIO.md`; do not aggregate beyond medians/ranges.

## L01 Units → Builder reconciliation — INVALID_SCOPE_SELECTION

- Verification timestamp (UTC): `2026-09-05T15:09:35.870Z`; verified SHA: `63390e64`; existing generation: `24586f47-c8bd-415a-9a43-cc77401a299b`.
- Provider-capacity generation `1 of 12` on the old SHA; the selected path lesson is position `0`, explicitly excludes solving, and its content does not match the campaign scenario `solve and check one-step linear equations`.
- Starting URL: `/units`; the approved Grade 7 Mathematics unit card was followed through the Units UI. Final URL: `/builder/6ebbcec4-fd94-494b-b163-ec4322ae2c3a`. No `/studio` URL was observed.
- Authenticated read-only requests observed/reconciled from the in-app page: `GET /api/v1/units/59ad0eb4-da1e-48d3-9cbe-efe4761e4eef` → `200`; `GET /api/v1/units/59ad0eb4-da1e-48d3-9cbe-efe4761e4eef/path` → `200`; `GET /api/v1/builder/lessons/6ebbcec4-fd94-494b-b163-ec4322ae2c3a` → `200`.
- Builder response reconciled `source_type=component_lectio`, `source_generation_id=24586f47-c8bd-415a-9a43-cc77401a299b`, and a present five-section document. Credentials, headers, prompts, and document prose were excluded.
- Builder linkage and UI interaction passed as subchecks. The `default` preset warning was confirmed and fixed separately.
- No generation, approval, retry, regeneration, provider, visual, or PDF request was initiated during this verification. Sanitized detailed evidence: `L01_UNITS_BUILDER_UI.md`.
- No L02 was started; this generation is excluded from campaign latency/pass statistics.

## Campaign gate — PAUSED_P0_UNITS_CUTOVER

## Post-cutover Run 6 — PASS

- The in-app browser began at /units and finished at the Builder route for
  ff310d12-a59c-41d5-bb85-cdfc248f8c69; the canonical history endpoint was
  used for dashboard reconciliation.
- Retired API probes returned sanitized HTTP 410 with code
  legacy_pipeline_retired for /api/v1/v3/* and /api/v1/legacy-units/*.
  Frontend legacy probes returned data-free retirement/404 responses.
- Available JSON logs were searched for /studio, /api/v1/v3, legacy,
  fallback, and concurrent. Studio/V3/legacy hits were explicit retirement
  probes only; fallback and concurrent had zero matches. No generation-flow
  Studio/V3 request or fallback was observed.
- Six provider calls were reconciled from llm_calls: DeepSeek,
  openai-compatible transport, api.deepseek.com, standard/fast lanes, six
  successes, zero failures. No visual request or transport retry was made.
- Detailed sanitized network/log evidence is in
  runs/RUN06-GRADE8-SOCIAL-STUDIES/RUN06_NETWORK_LOG_SUMMARY.md.

- T0 (UTC): `2026-09-05T09:56:19.979Z`; IAB network cursor at start: `639`; real-generation count: `0`.
- No CL-LOCAL-001 generation request is counted. The P0 scope blocker is that unit preparation redirects to Studio (`frontend/src/routes/units/[id]/+page.svelte:322-326`) and the bridge/initializer omits `chunked_state_json.control.pipeline` (`backend/src/planning/bridge.py:577-648`; `backend/src/generation/path_preparation.py:46-114`), which resolves to `v3_studio` when absent (`backend/src/generation/pipeline_dispatch.py:70-91`).
- Generation approval is only exposed by Studio (`frontend/src/routes/studio/+page.svelte:725`), so the campaign is paused before a valid Component Lectio run.

## Prior `/studio` pre-generation attempt — INVALID_SCOPE_LEGACY

- This sequence is retained separately and excluded from CL-LOCAL-001 and the real-generation count.
- IAB network cursor at start: `639`.
- `/v3/narrow`: request sequence `645`, response sequence `650`, finish sequence `652`; HTTP 200.
- `/v3/propose-intent`: request sequence `655`, response sequence `658`, finish sequence `660`; HTTP 200.
- `/v3/signals`: request sequence `663`, response sequence `668`, finish sequence `670`; HTTP 500, `text/plain`. UI reset with `Internal Server Error`; no manual retry.
- No approval-ready concept-plan generation was created. No generation SSE stream, document fetch, visual request, or PDF request occurred. Seven paid pre-generation calls are retained as legacy evidence only.
- Pre-run readiness boundary: `GET /health` → HTTP 200 at `2026-09-05T09:55:47Z`; sanitized request-id cursor `13c4e843`. A second readiness response was not retained, so no status is inferred for it here.
- Backend log cursor: active Uvicorn stdout is inherited/non-file-backed; use T0 UTC plus subsequent sanitized request IDs as the safe cursor. Startup stderr EOF offset at T0 was `442` bytes.
- No HAR or per-run network artifact exists; the sanitized IAB sequence above is the available network evidence.
