# Lesson Builder Merge Progress

Goal: Merge the Lesson Builder into the Textbook Agent as a polished, teacher-owned editing workspace.
Source of truth: `C:\Users\richi\Downloads\lesson-builder-unified-implementation-guide.md`

## Current Phase

- Phase 2 - Backend persistence
- Repo: `C:\Projects\Textbook agent`
- Status: completed

## Feature Checklist

### Feature: Builder Server Persistence

**Classification**: major
**Subsystems**: backend + frontend

### Progress
- [x] Understood requirements and identified scope
- [x] Read relevant source code and project rules
- [x] Implemented backend persistence table + API
- [x] Implemented frontend server-sync + IDB cache behavior
- [x] Wrote tests for new behavior
- [x] Ran validation (backend + frontend)
- [x] Self-reviewed against agents/standards/review.md
- [ ] Wrote commit message(s) following agents/standards/communication.md
- [ ] Updated PR description with summary, validation evidence, risks
- [x] Noted any follow-up work or open questions

### Validation Evidence
- Backend tests: `uv run pytest tests/routes/test_builder_lessons.py -q` passed (`4` tests).
- Backend lint: `uv run ruff check src tests/routes/test_builder_lessons.py` passed.
- Frontend checks: `npm run check` passed (`0` errors, `0` warnings).
- Frontend build: `npm run build` passed.

### Risks and Follow-up
- Status badge currently reflects latest local save/sync attempt; reconnect-triggered queue flush can recover in the background without immediately flipping toolbar state.
- Older Phase 1-only local IDB lessons without server records will show sync errors until recreated/migrated through server-backed flows.

## Phase 2 What Was Done

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
