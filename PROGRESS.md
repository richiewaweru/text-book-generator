# Lesson Builder Merge Progress

Goal: Merge the Lesson Builder into the Textbook Agent as a polished, teacher-owned editing workspace.
Source of truth: `C:\Users\richi\Downloads\lesson-builder-unified-implementation-guide.md`

## Current Phase

- Phase 1 - Move Builder into Textbook Agent frontend
- Repo: `C:\Projects\Textbook agent`
- Status: complete

## Feature Checklist

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