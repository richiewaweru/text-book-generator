# Legacy Removal Readiness Plan

**Disposition: `NOT YET — PLAN ONLY`**

This is an execution plan for retiring the V3 Studio/legacy path after the
Component Lectio migration has earned its stability evidence. It does not
authorize deletion, flag removal, production deployment, or a change to the
current campaign. The unrelated modified
`artifacts/reports/COMPONENT_LECTIO_PATCH_REPORT.md` remains protected.

## Summary

The new `/units` flow now dispatches to Component Lectio and can open a
canonical lesson in Builder. Run 3 is the first repaired local canary to pass
after the run-2 P1 content-quality fix; it is not the four-consecutive local
threshold and it does not establish hosted stability. V3 Studio remains the
explicit rollback and historical compatibility path.

The safe retirement shape is a staged strangler migration:

1. finish the designated four-consecutive local canaries and four hosted
   exact-SHA canaries;
2. move every new-lesson, navigation, dashboard, Builder recovery, pack, and
   print workflow to the new canonical path;
3. extract the shared contracts still imported from V3 Studio;
4. replace the last legacy persistence/recovery responsibilities;
5. prove zero runtime, UI, test, script, and route callers;
6. delete the legacy orchestrator, router, UI, session store, and adapters;
7. remove the active `v3_studio` flag/enum only after the historical-marker
   policy is implemented and verified.

## Current Problem

Legacy is not merely an unused screen. It is still mounted as a backend router,
contains the old generation orchestration and in-memory ownership state, owns
the V3-named HTTP API used by several screens, and is the source of some shared
DTO/prompt helpers used by the new path. It also remains coupled to pack/print
and historical-unit views.

The current migration contract explicitly preserved Studio as an explicit
rollback and prohibited deleting it in the cutover phase. The completed
proposal audit therefore means “new path is primary, legacy is removable after
proof,” not “legacy is already safe to delete.”

### Exact current callers and couplings

These are the current checkout references that must be retired, migrated, or
classified before deletion. Line numbers are repository-relative and refer to
the current `xplore` checkout; rerun the inventory immediately before each
deletion ticket.

| Area | Current caller/coupling | Required disposition |
|---|---|---|
| Backend composition | `backend/src/app.py:42` imports `V3GenerationWriter`; `backend/src/app.py:229-230` calls `fail_stale_running()` during startup; `backend/src/generation/routes.py:6,9` imports and mounts `v3_studio_router`. | Replace with pipeline-neutral recovery and the new route owner, then unmount. |
| Legacy HTTP/orchestration | `backend/src/generation/v3_studio/router.py:146` declares the `/v3` router. Its public operations include signals/narrow/propose-intent (`:409,432,513`), chunked plan/start/status/events (`:1524,1722,1740`), approve/regenerate/retry (`:2525,2636,2715`), generation start/history/detail/document (`:3147,3260,3291,3432`), component/card/visual repair (`:3824,3875,4004`), PDF (`:4077`), and trace endpoints (`:4203,4218`). | Migrate each live caller to a Units/Component Lectio contract or an extracted shared service; then delete the router. |
| Legacy process state | `backend/src/generation/v3_studio/session_store.py:133` creates `v3_studio_store`; the router uses it at `:615,853-880,967,1745-1770,2872-2885,3153-3157,3345-3382,3417-3421`. | Remove all request-time ownership/queue/blueprint state from the legacy store; use durable Component Lectio state or a narrowly scoped shared read model. |
| Pipeline rollback marker | `backend/src/core/config.py:11-12,129-134,187-194` accepts the `component_lectio`/`v3_studio` enum and rollback setting. `backend/src/generation/pipeline_dispatch.py:70-91` infers unmarked historical rows as `v3_studio`; `backend/src/generation/units_routes.py:136,276` still treats missing/legacy markers as V3. | Define and migrate the historical policy first; remove the active legacy enum only after all new rows and supported reads have a replacement. |
| Legacy writer/recovery | `backend/src/generation/v3_studio/generation_writer.py:283` defines `V3GenerationWriter`; its stale recovery implementation is `:746`, and router lifecycle calls occur at `router.py:738,1217,1612,2549,2686,2738,2766,2909,3174,3266,3296,3347,3400,3438,3835,3882,4016,4085`. | Mine/replace status, terminal persistence, retry, document, and telemetry behavior in a pipeline-neutral service; then delete the writer. |
| PDF coupling | `backend/src/generation/pdf_export/service.py:209-249` defines `export_v3_studio_pdf()` and renders `/studio/print/{generation_id}`; the legacy router invokes it at `router.py:4111`. | Make PDF consume a canonical `LessonDocument`/generation projection, verify H02/H06-style designated PDF checks, then retire the V3-specific export function. |
| New-lesson navigation | `frontend/src/lib/components/workspace/NewLessonSplitButton.svelte:29` still links `+ New lesson` to `/studio`. | Link to the Units constructor after the Units flow has an explicit empty/new state and auth routing. |
| Dashboard/history | `frontend/src/routes/lessons/+page.svelte:6,17-19,178-216` imports V3 API/types and loads V3 documents/history; actions are rendered at `:282-312,350-367`. `frontend/src/routes/lessons/+page.svelte:17` still types documents as V3 packs. | Use a generation-history/document projection that can represent Component Lectio directly; preserve historical read-only rows explicitly. |
| Builder generation/recovery | `frontend/src/routes/builder/[id]/+page.svelte:12-20` imports V3 APIs, V3 types, and the conditional adapter; `:92-168` polls V3 status/document; `:354-359` sends failed recovery to `/studio`. `frontend/src/lib/builder/adapters/from-generation.ts:1-8,15,95-117` keeps the V3 adapter branch. | Replace V3-named polling and recovery with a pipeline-neutral API and direct canonical document loading; retain a separately tested historical reader until the history decision is complete. |
| Studio UI/store | `frontend/src/routes/studio/+page.svelte:6-46` imports the V3 surface, API, store, canvas, booklet, document, print, and adapter modules; the approval/generation flow is at `:648-865`. `frontend/src/lib/stores/v3-studio.svelte.ts:12-71` owns the V3 session state. | Move any still-needed shared view primitives to neutral modules; remove the route and store after zero callers. |
| V3 API client | `frontend/src/lib/api/v3.ts:35-473` implements signals, narrowing, intent, planning, approval, retry, status, streaming, documents, history, repairs, and PDF against `/api/v1/v3`. | Replace with Units/Component Lectio API modules or a deliberately named generation client; no broad URL rename until callsites are migrated and tested. |
| Pack/editor links | `frontend/src/routes/packs/[pack_id]/+page.svelte:8,129-130,163-167` uses V3 pack APIs and links editors to `/studio/generations`; `frontend/src/routes/packs/[pack_id]/print/+page.svelte:5-10,49-60` adapts V3 packs for print. | Migrate active packs to canonical lesson/document projections; classify old packs as read-only or retain a time-bounded compatibility reader. |
| Legacy unit history | `backend/src/planning/compatibility.py:17,39-66,66-131` serves `/api/v1/legacy-units`; it filters V3/v3-studio generations at `:83-95,116-131`. `frontend/src/routes/units/+page.svelte:4,14,34,288-293` lists compatibility wrappers; `frontend/src/routes/units/legacy/[pack_id]/+page.svelte:4,21,38-42` links each resource to Legacy Studio. | Decide separately whether this is a read-only history surface, a migrated projection, or a time-boxed removal. Do not delete by implication. |
| Legacy generation detail/print | `frontend/src/routes/studio/generations/[id]/+page.svelte:5-9,42-92` loads V3 detail/document/PDF; `frontend/src/routes/studio/print/[id]/+page.svelte:11-18,50-100` fetches `/api/v1/v3/.../document` and adapts it. | Replace with canonical document/detail/print routes, then remove the routes and adapter. |
| Shared backend imports | Component Lectio still imports V3-owned DTOs in `backend/src/generation/component_lectio/service.py:35`, `backend/src/generation/component_lectio/launcher.py:11`, and `backend/src/generation/path_preparation.py:10`; planning/execution imports remain in `backend/src/v3_execution/runtime/stage2_lanes.py:15`, `backend/src/v3_blueprint/planning/retry.py:10`, `section_expander.py:14-16`, `persistence.py:14`, `structural_planner.py:11-12`, and `backend/src/v3_execution/compile_orders.py:29`. | Extract DTOs, prompts, signal maps, and only genuinely shared planner/executor contracts into neutral modules. Keep `v3_blueprint`/`v3_execution` only where the new path still has verified ownership; do not delete shared runtime code merely because its directory name says V3. |

## Target State

- `/units` is the only new-lesson and new-generation entrypoint. `/studio` is
  neither linked nor used as an automatic fallback.
- The active generation API is pipeline-neutral or explicitly Component
  Lectio-named, persists a canonical `LessonDocument`, and exposes status,
  recovery, history, and PDF through the same source of truth.
- Builder polls and recovers through the canonical generation contract. A
  failed Component Lectio generation cannot silently open or execute Studio.
- Active packs and print use canonical documents. Any retained legacy history
  is read-only, clearly labelled, and never an input to new generation.
- No Component Lectio module imports `generation.v3_studio`; remaining shared
  imports point to neutral contracts or verified shared runtime modules.
- Startup stale recovery is pipeline-neutral, durable, bounded, and tested for
  Component Lectio. It does not instantiate the deleted V3 writer.
- New rows have an explicit pipeline marker. Historical rows have a documented
  read policy and remain readable without keeping the full legacy execution
  stack alive.
- Static search and runtime telemetry show zero legacy execution callers before
  deletion. The only remaining references are historical documentation,
  migration tests, or an explicitly approved read-only compatibility module.

## Constraints and Locked Decisions

- Disposition remains `NOT YET — PLAN ONLY`; this artifact does not delete
  anything.
- Complete the campaign evidence gate first: the designated four consecutive
  local `PASS`/`PASS_WITH_RECOVERY` runs on one exact tested SHA, followed by
  four hosted canaries on that exact SHA, one Railway replica and one worker.
- Run 3 is the first repaired passing local canary, not the stability
  threshold. It must not be used to justify deletion or hosted promotion.
- Keep all provider work serial. Do not exceed the campaign's twelve planned
  real generations without explicit authorization.
- Keep Component Lectio as the default and keep V3 Studio as an explicit
  rollback while the migration is in flight. There is no automatic fallback.
- Public interfaces remain unchanged until their replacement has parity and a
  reviewed migration; a V3-named endpoint may temporarily dispatch through a
  thin authority.
- No production deployment, multi-worker generation, DB-backed multi-process
  leasing expansion, metrics table, or unrelated cleanup is part of this plan.
- Preserve the protected patch report and all unrelated user changes.

## Design Choices

### Staged strangler, not a big-bang delete

Migrate one consumer family at a time while the explicit rollback remains
available. This keeps failures attributable and permits a deployment revert.
The trade-off is a temporary compatibility surface and more zero-caller work.

### Canonical document first

Make `LessonDocument` and durable generation projections authoritative for active
flows. V3 packs may be decoded for history during the transition, but new
Component Lectio output must not be converted into a V3 pack and back.

### Read-only legacy history is a separate product decision

The `/legacy-units` wrapper is not an execution caller by itself, but its detail
links currently open Studio. Decide whether to render old rows from a frozen
projection, migrate them, or remove them after a retention window. No deletion
ticket may infer this decision from the new-generation canary result.

### Extract shared contracts before deleting their current owner

Move DTOs, prompts, signal maps, and helper functions into neutral packages with
tests and compatibility imports as needed. Keep the execution engine only when
its ownership is proven by current Component Lectio tests and canaries.

### Preserve historical identity without preserving historical execution

Keep the persisted pipeline marker as data. New generations must explicitly say
`component_lectio`; pre-cutover unmarked rows remain resolvable under an
approved legacy-history policy. Removing the active `v3_studio` enum must not
make historical rows unreadable; use a stable historical marker/decoder or a
read-only projection before removing the execution enum.

## Recommended Plan

### Phase 0 — Evidence gate (before any legacy removal work)

1. Complete the remaining local scenarios and the designated four-consecutive
   local gate on one exact SHA. Reconcile browser, logs, network, and DB after
   each run; record medians/ranges only.
2. Deploy that exact SHA to staging/canary Vercel and Railway, prove the SHA,
   migration, environment, one replica, one worker, health, image readiness,
   logs, and DB access, then complete four hosted canaries.
3. Stop on P0; patch and relabel for P1; record P2 without broad cleanup.
4. Do not begin a legacy deletion branch from a SHA that has not passed the
   evidence gate. Run 3 is evidence for progress only.

### Phase 1 — Migrate user entrypoints and dashboard

Replace the New Lesson link, dashboard create actions, generation-history
loading, and any completion links with `/units` and canonical generation
projections. Keep the old URLs returning an explicit compatibility response or
read-only view while links drain; do not redirect new generation into Studio.

### Phase 2 — Replace Builder V3 APIs and recovery

Introduce a pipeline-neutral Builder generation client for status, document
polling, terminal state, save/reload, and recovery. Preserve direct
Component-Lectio document loading. Replace “Open recovery in Studio” with a
Builder/Units recovery action whose semantics are backed by durable checkpoints.

### Phase 3 — Migrate packs and print

Define the canonical pack/document projection for active lessons, migrate pack
editor links, and make PDF render from that projection. Validate print readiness,
PDF export/open, and save/reload on the designated local/hosted scenarios before
removing the V3-specific print route or adapter.

### Phase 4 — Decide legacy unit history separately

Choose one of: (a) retain a time-boxed read-only projection, (b) migrate each
historical generation to a canonical immutable document, or (c) remove the
compatibility surface after an announced retention policy. The decision must
specify what `/api/v1/legacy-units`, `/units/legacy/*`, old pack IDs, and old
generation IDs do after removal. Until then, keep these reads isolated from new
generation and label them legacy.

### Phase 5 — Extract shared DTOs, prompts, and signal helpers

Move the still-used V3-owned DTOs, prompt fragments, signal maps, and narrow
helpers into neutral modules. Update Component Lectio and the retained history
reader to import the neutral owners. Remove compatibility aliases only after
static and runtime caller searches are clean.

### Phase 6 — Historical marker policy and recovery replacement

Write and migrate the policy for marked, unmarked, failed, and deleted legacy
rows. Replace `V3GenerationWriter.fail_stale_running()` with a pipeline-neutral
stale-recovery service that uses durable generation state, records a structured
reason, and has no V3-specific import. Verify restart recovery on PostgreSQL and
ensure a deleted legacy executor is never selected for a new generation.

### Phase 7 — Zero-caller gate and deletion

Run the repository-wide inventory again, including source, tests, scripts,
route manifests, frontend imports, and deployment configuration. Require zero
runtime callers for every legacy deletion group and an explicit decision for
read-only history. Then delete in this order: orchestrator internals and
router; session store; Studio UI routes/components/store; V3 pack→Lectio and
Builder adapters; V3-specific PDF glue; finally the active `v3_studio` flag and
enum. Leave only historical decoders/projections that the policy explicitly
requires.

## Work Breakdown / Tickets

### LR-01 — Stability evidence gate

**Scope:** complete the local/hosted canary sequence on one exact SHA.

**Acceptance criteria:**

- The designated four consecutive local runs and four hosted runs are
  `PASS`/correctly scoped `PASS_WITH_RECOVERY` with valid documents.
- Browser, DB, logs, network, worker/replica, migration, and SHA evidence is
  recorded per run; no P0 or unresolved single-worker P1 remains.
- Run 3 is labelled “first repaired canary,” never “threshold met.”

**Rollback:** no code rollback; pause the campaign and keep the explicit
`GENERATION_PIPELINE_DEFAULT=v3_studio` deployment rollback available.

### LR-02 — New lesson, navigation, and dashboard cutover

**Scope:** `NewLessonSplitButton`, dashboard history/create actions, auth-safe
links, and completion destinations.

**Acceptance criteria:**

- All new-lesson actions open `/units`; no new-generation link opens `/studio`.
- Dashboard loads Component Lectio documents without V3 pack coercion.
- Existing historical links have a tested, labelled compatibility behavior.

**Rollback:** revert the frontend deployment; restore the prior links while the
legacy route remains available.

### LR-03 — Pipeline-neutral Builder API and recovery

**Scope:** Builder polling, status/document loading, terminal errors, retry and
recovery affordances.

**Acceptance criteria:**

- Builder uses canonical generation APIs for Component Lectio and never silently
  falls back to Studio.
- Save/reload and terminal-state tests pass for success and failure.
- Legacy history, if retained, is explicitly routed to a read-only reader.

**Rollback:** revert the Builder client and keep the old V3 adapter only for
historical generations; do not change persisted pipeline markers.

### LR-04 — Canonical pack and print projection

**Scope:** active pack links, print pages, PDF service, and answer-key paths.

**Acceptance criteria:**

- Active lessons print from canonical `LessonDocument` data.
- Designated PDF export/open checks pass locally and hosted.
- No active Component Lectio flow imports the V3 pack adapter.

**Rollback:** revert pack/print routes; retain the legacy read-only print route
until the canonical projection is revalidated.

### LR-05 — Legacy unit history decision

**Scope:** `/api/v1/legacy-units`, `/units/legacy/*`, old pack/generation IDs.

**Acceptance criteria:**

- A written decision names retention, read-only behavior, deletion timing, and
  404/redirect behavior for each old surface.
- If retained, it has no new-generation or mutable Studio action and has tests
  against historical rows.
- If removed, a data/export/communication note and migration/retention check
  are recorded.

**Rollback:** restore the read-only compatibility route from the prior commit;
never restore it as a hidden new-generation fallback.

### LR-06 — Extract shared contracts

**Scope:** DTOs, prompts, signal maps, and helpers currently owned by
`generation.v3_studio`.

**Acceptance criteria:**

- Component Lectio and retained readers import neutral modules.
- Unit tests cover the extracted contracts and preserve public behavior.
- `rg` finds no Component Lectio import from `generation.v3_studio`.

**Rollback:** retain compatibility re-export shims in the old module while
callers are migrated; revert only the extraction commit if behavior changes.

### LR-07 — Historical marker and stale recovery replacement

**Scope:** marker resolution, old rows, startup stale recovery, structured
recovery telemetry.

**Acceptance criteria:**

- New rows always persist `component_lectio`; old unmarked rows follow the
  approved read-only policy.
- Restart recovery is durable, deterministic, pipeline-neutral, and tested on
  PostgreSQL; no `V3GenerationWriter` import remains in app startup.
- Active legacy enum removal cannot make retained historical rows unreadable.

**Rollback:** revert the recovery service and restore the explicit legacy flag
only while the old writer/router still exists; do not mix marker semantics.

### LR-08 — Zero-caller audit and legacy deletion

**Scope:** delete the legacy orchestrator/router, session store, UI/store,
adapters, and then active flag/enum.

**Acceptance criteria:**

- Static search has zero runtime/test/script/deployment callers for each group,
  or a documented approved historical reader is the only remaining reference.
- Route manifests and frontend builds contain no deleted route/import.
- Full backend/frontend/tooling/architecture validation passes, migration
  upgrade/downgrade/upgrade passes, and post-deploy canary health passes.
- A revert commit/deployment is prepared before deletion; no protected report
  or unrelated change is staged.

**Rollback:** before flag/enum deletion, redeploy the last known-good SHA and
set `GENERATION_PIPELINE_DEFAULT=v3_studio` only if the legacy route remains.
After deletion, rollback is a deployment/code revert to the last legacy-capable
SHA; the removed enum is not a recovery mechanism.

## Expected Impact

- New teachers see one coherent Units → Component Lectio → Builder workflow.
- Failure and recovery behavior is easier to reason about because it uses one
  durable document/status authority.
- The runtime sheds a large in-memory Studio session/orchestration surface and
  reduces the chance of hidden legacy execution.
- Historical data remains governed by an explicit retention decision instead of
  being accidentally broken by route deletion.
- Temporary migration work increases test and compatibility surface until the
  zero-caller gate is complete.

## Risks and Open Questions

- **Historical rows:** Should old V3 packs be rendered forever, migrated to an
  immutable canonical projection, or retained for a fixed period? Who owns the
  retention decision?
- **Public V3 URLs:** What exact status/redirect/404 contract is required for
  bookmarked `/studio` and `/api/v1/v3` links?
- **Pack semantics:** Which pack/editor and shared-quiz workflows are still
  supported product behavior versus historical artifacts?
- **PDF parity:** Does the canonical renderer cover booklet/answer-key features
  currently implemented only by V3 print code?
- **Shared runtime naming:** `v3_blueprint` and `v3_execution` contain code
  used by Component Lectio. Their names alone are not deletion criteria; each
  module requires a caller and ownership audit.
- **Distributed leases:** DB-backed multi-process leasing remains out of scope;
  hosted proof must continue to use one worker/replica and report this known
  limitation.
- **Rollback window:** How long should the explicit V3 rollback deployment be
  retained after hosted stability and before flag removal?

## Validation Plan

### Before each migration ticket

- Confirm clean intended diff, preserved protected report, exact source SHA, and
  current campaign disposition.
- Run targeted tests for the affected route/document/recovery contract.
- Re-run `rg` caller inventory and record additions/removals in the campaign
  evidence without counting comments or archived proposal text as callers.

### Before zero-caller approval

- `python tools/agent/validate_repo.py --scope all` in an isolated temporary
  test directory.
- `npm run check` and `npm run build` in `frontend/`.
- Architecture audit and all Component Lectio final-contract, pre-live,
  cutover, and E2E suites.
- PostgreSQL migration upgrade → downgrade → upgrade and restart/stale-recovery
  tests against the dedicated campaign-shaped schema.
- Frontend route smoke checks for `/units`, dashboard, Builder, packs, print,
  and the chosen historical policy.

### Zero-caller gates

For each deletion group, require all of the following before merging:

1. `rg` shows zero imports, route mounts, navigation links, API calls, tests,
   scripts, and deployment references outside approved historical evidence.
2. Runtime log search over the full canary window shows no legacy route,
   `v3_studio` execution, session-store, or V3 adapter events for new lessons.
3. DB query confirms no new generation is marked `v3_studio`, and retained old
   rows are readable under the historical policy.
4. Browser checks prove no hidden Studio fallback, valid Builder documents,
   truthful terminal states, save/reload, and designated PDF behavior.
5. The exact tested SHA is deployed to staging/canary and a reversible release
   point is recorded.

### Final deletion validation

After LR-08, run the full validation suite again, inspect the route manifest and
production build output for orphaned imports, verify historical marker decoding,
and perform one smoke test per supported active workflow. Only then may the
campaign be marked stable and the active legacy flag/enum considered removed.

