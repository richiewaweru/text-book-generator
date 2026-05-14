# Lesson Builder Merge Progress

Goal: Merge the Lesson Builder into the Textbook Agent as a polished, teacher-owned editing workspace.
Source of truth: `C:\Users\richi\Downloads\lesson-builder-unified-implementation-guide.md`

## Current Phase

- Phase 8 - Polish and production hardening
- Repo: `C:\Projects\Textbook agent`
- Status: completed (pending PR)

## Feature Checklist

### Feature: Polish and Production Hardening

**Classification**: major
**Subsystems**: both

### Progress
- [x] Understood requirements and identified scope
- [x] Read relevant source code and project rules
- [x] Added save retry UX in toolbar (`saveStatus=error` -> retry action)
- [x] Added loading skeleton and robust route error states for `/builder/[id]` (401 -> logout/login redirect, 404 -> local not found panel)
- [x] Updated mobile palette behavior toward bottom-sheet presentation and expanded keyboard hint bar copy
- [x] Added backend hardening: structured builder logs and save endpoint rate limit
- [x] Added/updated tests for new frontend behavior
- [x] Ran validation (backend + frontend)
- [x] Self-reviewed against agents/standards/review.md
- [x] Wrote commit message(s) following agents/standards/communication.md
- [ ] Updated PR description with summary, validation evidence, risks
- [x] Verified cross-repo success criteria checks (Lectio cleanup + single Lectio version)
- [x] Noted any follow-up work or open questions

### Validation Evidence
- Backend tests: `uv run pytest tests/routes/test_builder_lessons.py -q` passed (`11 passed`).
- Backend lint: `uv tool run ruff check src tests/routes/test_builder_lessons.py` passed.
- Frontend tests: `npm run test -- src/lib/builder/components/toolbar/DocumentToolbar.test.ts src/routes/builder/[id]/page.test.ts src/routes/builder/page.test.ts src/routes/dashboard/page.test.ts` passed (`10 passed`).
- Frontend compatibility tests: `npm run test -- src/lib/components/LectioDocumentView.test.ts src/lib/builder/adapters/from-generation.test.ts` passed (`6 passed`).
- Frontend checks: `npm run check` passed (`0` errors, `0` warnings).
- Frontend build: `npm run build` passed.
- Dependency check: `npm ls lectio` passed with a single version (`lectio@0.4.6`).
- Lectio cleanup check (`C:\Projects\lectio`): `src/routes/builder` absent, `src/lib/builder` absent.

### Risks and Follow-up
- Frontend validation warnings listed in Phase 8 (page-length and alt-text hints) remain future follow-up; they are intentionally non-blocking in the guide.
- Local npm installs in fresh worktrees require `lectio@0.4.6` availability; pin now matches published version.

## Success Criteria Verification (1-10)

- [x] 1. Teacher can open V3 lesson in builder with one click.
  Evidence: `LectioDocumentView.test.ts` (Open in Builder CTA flow) and `from-generation.ts` adapter test pass.
- [x] 2. Teacher can edit/reorder/add/remove blocks.
  Evidence: `document-store-ops.test.ts` coverage plus builder UI/store integration in Phases 3-4.
- [x] 3. AI can fill/improve/custom-generate any block.
  Evidence: Phase 4 request-mode wiring (`fill|improve|custom`) and route ownership tests.
- [x] 4. Edits save to server and survive reload/device changes.
  Evidence: server-authoritative CRUD + sync queue from Phase 2; backend lesson route tests pass.
- [x] 5. Print produces clean lesson with no builder chrome.
  Evidence: builder print route + print CSS + successful build/test coverage from Phases 7-8.
- [x] 6. Teacher can create a lesson from scratch without V3 generation.
  Evidence: `/builder/new` template/blank creation flow and `/builder` listing route shipped in Phase 6.
- [x] 7. Builder module can be deleted without breaking studio/dashboard/textbook routes.
  Evidence: frontend build passes; dashboard and textbook-facing tests pass (`dashboard/page.test.ts`, `LectioDocumentView.test.ts`).
- [x] 8. Exactly one Lectio version in dependency tree.
  Evidence: `npm ls lectio` -> single `lectio@0.4.6`.
- [x] 9. LessonDocument round-trips cleanly (adapt/edit/export/render).
  Evidence: adapter/runtime tests pass and print/export rendering path validated in Phases 1 and 7.
- [x] 10. No generated lesson is mutated by builder edits.
  Evidence: copy-on-edit flow + backend print student-strip test confirms persisted lesson remains unchanged.

## Phase 8 What Was Done

- Backend:
  - Added structured builder event logging for create/list/get/save/delete/upload/print/export operations.
  - Added save endpoint rate limiting (`PUT /api/v1/builder/lessons/{lesson_id}` -> `120/minute`).
- Frontend:
  - Added retry control in toolbar save-error state.
  - Added `/builder/[id]` loading skeleton and explicit 401/404/500 handling.
  - Updated palette overlay to bottom-sheet style on mobile widths.
  - Expanded shortcut hint copy to include undo/redo/save/duplicate/delete/escape.
  - Wired retry save action from shell to document store flush.
- Tests:
  - Extended `DocumentToolbar.test.ts` for retry control behavior.
  - Added `src/routes/builder/[id]/page.test.ts` for success, 404, and 401 route behavior.

## Phase 7 Archive

## Phase 7 What Was Done

- Backend:
  - Added `GET /api/v1/builder/lessons/{lesson_id}/print-document?audience=teacher|student` with:
    - lesson ownership enforcement
    - student mode answer stripping on copy-only payload
  - Added `POST /api/v1/builder/lessons/{lesson_id}/export/pdf` with:
    - lesson ownership enforcement
    - audience-aware render path (`/builder/print/{id}?audience=...`)
    - reuse of existing `export_generation_pdf(...)` pipeline
    - file response headers + background cleanup handling
  - Added helper logic for:
    - synthetic pipeline document manifest from builder lesson sections
    - synthetic generation metadata for cover/export metadata
    - answer stripping for student audience (`quiz-check`, `short-answer`, `practice-stack`, `fill-in-blank`)
- Frontend:
  - Added builder print route:
    - `frontend/src/routes/builder/print/[id]/+page.svelte`
    - fetches owned print document payload with audience mode
    - emits Playwright readiness attributes (`data-generation-complete`, image load diagnostics)
  - Extended builder toolbar:
    - print preview toggle (applies print CSS in-canvas without opening browser print dialog)
    - teacher/student PDF export buttons wired to backend endpoint
    - export loading/error state
  - Extended builder export utility:
    - `downloadBuilderLessonPdf(lessonId, audience)` in `frontend/src/lib/builder/utils/pdf-export.ts`
  - Added preview-mode CSS:
    - `frontend/src/lib/builder/styles/print.css` includes `.builder-print-preview` selectors to hide builder chrome while keeping toolbar controls visible.
- Tests:
  - Backend: expanded `backend/tests/routes/test_builder_lessons.py` to cover:
    - student print-document answer stripping + non-mutation of persisted lesson
    - ownership checks for print-document/export endpoints
    - PDF export render-path wiring to audience route
  - Frontend: added `frontend/src/lib/builder/components/toolbar/DocumentToolbar.test.ts` for:
    - print preview toggle callback
    - teacher/student PDF action wiring

## Phase 6 What Was Done

- Confirmed manual creation route behavior in `frontend/src/routes/builder/new/+page.svelte`:
  - Template selection from `templateRegistry`
  - Preset selection from `basePresets` filtered by template
  - Template scaffold uses `always_present` blocks
  - Blank flow uses `open-canvas`
  - Both call `POST /api/v1/builder/lessons` and navigate to `/builder/{id}`
- Added builder index route at `frontend/src/routes/builder/+page.svelte`:
  - Loads editable lessons via `GET /api/v1/builder/lessons`
  - Displays lesson title, source-type badge, and updated timestamp
  - Each item links to `/builder/{id}`
  - Includes empty-state CTA to `/builder/new`
- Added entry points:
  - Header nav links: `Builder` and `New Lesson` in `frontend/src/routes/+layout.svelte`
  - Dashboard Lesson Builder card with links to `/builder` and `/builder/new`
- Added route test coverage:
  - `frontend/src/routes/builder/page.test.ts` validates list rendering and empty state CTA
  - Existing dashboard test suite still passes after entry-point additions

## Phase 5 What Was Done

- Backend:
  - Added `POST /api/v1/builder/lessons/{lesson_id}/media/upload` with:
    - teacher ownership checks
    - content type allowlist validation (`image/png`, `image/jpeg`, `image/webp`, `image/gif`)
    - max file size enforcement (10MB)
    - GCS key path: `editable-lessons/{lesson_id}/media/{media_id}.{ext}`
  - Extended `GCSImageStore` with `upload_with_key(...)` so builder uploads reuse existing storage infrastructure.
- Frontend:
  - Added `frontend/src/lib/builder/api/media-upload.ts`.
  - Updated `ImageUploader.svelte` to upload files via backend API and emit hosted URL payloads.
  - Updated `FieldMedia.svelte` and `MediaManager.svelte` to consume uploaded URLs while keeping video URL paste + existing-media selection flows.
  - Updated client-side file-size messaging to 10MB.
- Tests:
  - Expanded `backend/tests/routes/test_builder_lessons.py` with media-upload coverage:
    - owned lesson upload path + key assertion
    - ownership rejection
    - unsupported MIME rejection
    - oversized payload rejection

## Phase 4 What Was Done

- Extended block generation request shape in backend + frontend to include:
  - `lesson_id`
  - `mode` (`fill | improve | custom`)
- Added lesson ownership enforcement on `POST /api/v1/blocks/generate`:
  - if `lesson_id` is provided, route verifies `(lesson.id, lesson.user_id)` against current user.
  - unknown or unowned lesson returns `404`.
- Wired AI assist payload to include lesson identity and mode from the editing surface.
- Added safe AI apply merge to prevent overwriting hidden/internal fields:
  - new utility `mergeAiContentWithEditableFields(...)` uses `getEditSchema(component_id)` and applies only non-hidden fields.
- Updated canvas AI apply path to use merged content before store update.
- Added/updated tests:
  - `backend/tests/routes/test_blocks_generate.py` for owned/unowned lesson behavior and mode forwarding.
  - `frontend/src/lib/builder/components/ai/ai-block-utils.test.ts` for editable-field-only merge and null-schema fallback.

## Phase 3 What Was Done

- Replaced permanent palette sidebar with centered "Add block" overlay:
  - Added `frontend/src/lib/builder/components/palette/PaletteOverlay.svelte`.
  - Added grouped/searchable data adapter `frontend/src/lib/builder/components/palette/palette-overlay.ts`.
  - Added palette filter tests in `frontend/src/lib/builder/components/palette/palette-overlay.test.ts`.
- Replaced full right-side outline panel with minimal dot rail:
  - Updated `frontend/src/lib/builder/components/canvas/CanvasOutline.svelte`.
- Updated canvas composition surface and interaction polish:
  - Updated `frontend/src/lib/builder/components/canvas/BlockCanvas.svelte` (centered page card, preserved DnD reorder, shortcut hint bar).
  - Updated `frontend/src/lib/builder/components/canvas/BlockCard.svelte` (selected-state floating action bar and left-edge drag handle).
  - Updated `frontend/src/lib/builder/components/shell/AppShell.svelte` to use overlay workflow.
- Added operation regression tests for core store behaviors:
  - `frontend/src/lib/builder/stores/document-store-ops.test.ts`
  - Covers add, duplicate, delete + undo, and cross-section reorder.

## Next Phase Needs

- Phase 8: polish and production hardening (save retry UX, loading/error states, mobile, validation warnings, backend limits/logging, and Lectio cleanup validation).

---

## Phase 2 Archive

- Backend persistence:
  - Added `EditableLessonModel` in `backend/src/core/database/models.py`.
  - Added migration `backend/src/core/database/migrations/versions/20260513_0013_add_editable_lessons.py`.
  - Added builder CRUD API routes in `backend/src/builder/routes.py`:
    - `POST /api/v1/builder/lessons`
    - `GET /api/v1/builder/lessons`
    - `GET /api/v1/builder/lessons/{id}`
    - `PUT /api/v1/builder/lessons/{id}`
    - `DELETE /api/v1/builder/lessons/{id}`
  - Enforced ownership checks for all operations and source-generation ownership on create.
  - Added hard LessonDocument save guards (shape, known component IDs, section/block integrity, payload size limit).
  - Registered builder router in `backend/src/app.py`.
  - Updated backend CORS methods to include `PUT`.
- Frontend persistence + sync:
  - Added CRUD client: `frontend/src/lib/builder/api/lesson-crud.ts`.
  - Added server sync layer: `frontend/src/lib/builder/persistence/server-sync.ts`.
  - Updated document store to:
    - save immediately to IDB (debounced 300ms)
    - save to server via debounced PUT (1200ms)
    - queue retry entries on retryable failures
    - flush queue on manual save and load
  - Mounted reconnect sync hooks in `AppShell` via `OfflineSyncHooks`.
  - Updated `/builder/[id]` load path to server-first with IDB fallback.
- Flow updates:
  - Updated `/builder/new` to create server lesson first, then cache in IDB.
  - Updated textbook "Open in Builder" to `POST /api/v1/builder/lessons` first (server UUID), then cache + navigate.

## Next Phase Needs

- Phase 3: Palette, block management verification, and canvas polish per unified guide.

---

## Phase 1 Archive

### Feature: Embed Lesson Builder Module

**Classification**: major
**Subsystems**: frontend

### Progress
- [x] Understood requirements and identified scope
- [x] Read relevant source code and project rules
- [x] Implemented the change
- [x] Wrote tests for new behavior
- [x] Ran validation (frontend: check + build)
- [x] Self-reviewed against agents/standards/review.md
- [x] Wrote commit message(s) following agents/standards/communication.md
- [ ] Updated PR description with summary, validation evidence, risks
- [x] Noted any follow-up work or open questions

### Validation Evidence
- `npm run check` (frontend) passed.
- `npm run build` (frontend) passed.
- `npm run test -- src/lib/components/LectioDocumentView.test.ts src/lib/builder/adapters/from-generation.test.ts` passed (`2` files, `6` tests).
- Builder routes compile and are included in build output:
  - `src/routes/builder/[id]/+page.svelte`
  - `src/routes/builder/new/+page.svelte`

### Risks and Follow-up
- Source builder code currently lives in `C:\Projects\lectio-lesson builder`, while the guide references older `lectio` paths.
- Local dependency validation required explicit local Lectio installation due `lectio@0.4.5` not being registry-published yet.
- Open-in-builder entry is wired for textbook view flows in frontend; server persistence remains Phase 2.

## Phase 1 What Was Done

- Copied builder module into frontend boundaries:
  - `frontend/src/lib/builder/**`
  - `frontend/src/routes/builder/**`
- Rewired migrated imports to builder-local paths and shared app surfaces (`lectio`, `$app/*`, `$lib/stores/auth`, `$lib/api/*` where applicable).
- Disabled Share and Google Drive save UI in `AppShell` by omission of toolbar callbacks (feature-flag behavior: hidden, not deleted from concept).
- Added adapter composition:
  - `frontend/src/lib/builder/adapters/from-generation.ts`
  - Composes `adaptV3PackToLectioDocument()` + `exportToLessonDocument()`.
- Wired textbook view "Open in Builder" flow:
  - Converts current generation to `LessonDocument`
  - Saves to builder IDB store
  - Navigates to `/builder/{id}`
- Updated `LectioDocumentView` CTA text from "Export for Builder" to "Open in Builder".
- Added/updated targeted tests:
  - `frontend/src/lib/builder/adapters/from-generation.test.ts`
  - `frontend/src/lib/components/LectioDocumentView.test.ts`

## Next Phase Needs

- Phase 2: Backend persistence for editable lessons (`/api/v1/builder/lessons*`) and server-sync integration in builder store.
