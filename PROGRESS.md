# Lesson Builder Merge Progress

Goal: Merge the Lesson Builder into the Textbook Agent as a polished, teacher-owned editing workspace.
Source of truth: `C:\Users\richi\Downloads\lesson-builder-unified-implementation-guide.md`

## Current Phase

- Phase 5 - Shared media manager with server uploads
- Repo: `C:\Projects\Textbook agent`
- Status: completed

## Feature Checklist

### Feature: Shared Media Manager with GCS Upload

**Classification**: major
**Subsystems**: backend + frontend

### Progress
- [x] Understood requirements and identified scope
- [x] Read relevant source code and project rules
- [x] Implemented lesson-owned media upload endpoint (`POST /api/v1/builder/lessons/{id}/media/upload`)
- [x] Enforced media upload type and size validation (PNG/JPEG/WebP/GIF, 10MB max)
- [x] Routed image upload UI through backend API (no data-URI persistence for new uploads)
- [x] Preserved URL-paste and existing-media selection flows in editor/media manager
- [x] Wrote tests for new behavior
- [x] Ran validation (backend + frontend)
- [x] Self-reviewed against agents/standards/review.md
- [x] Wrote commit message(s) following agents/standards/communication.md
- [ ] Updated PR description with summary, validation evidence, risks
- [x] Noted any follow-up work or open questions

### Validation Evidence
- Backend lint: `uv run ruff check src tests/routes/test_builder_lessons.py` passed.
- Backend tests: `uv run pytest tests/routes/test_builder_lessons.py -q` passed (`8 passed`).
- Frontend checks: `npm run check` passed (`0` errors, `0` warnings).
- Frontend build: `npm run build` attempted; failed due pre-existing local `lectio` install mismatch/resolution issue in this environment (`Rollup failed to resolve import "lectio"` from existing route code).

### Risks and Follow-up
- Upload endpoint currently relies on `GCSImageStore` availability (`GCS_BUCKET_NAME` + credentials); when unavailable it returns `503`.
- Current `lectio` package in this workspace does not expose `MediaReference.source`; frontend media entries stay schema-compatible by omitting that field.

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

- Phase 6: manual lesson creation UX verification and builder lesson-list entry path hardening.

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
