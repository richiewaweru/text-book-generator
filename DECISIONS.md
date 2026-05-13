# Lesson Builder Merge Decisions

## Phase 1 - Move Builder into Textbook Agent frontend

### Decision: Use `lectio-lesson builder` as migration source
- **Context:** The unified guide's Phase 1 FROM/TO map references builder folders inside `lectio`, but the current `lectio` repo no longer has those builder routes/components.
- **Guide says:** Move builder code into textbook agent frontend and keep Lectio as package-only contract/render layer.
- **Chose:** Use `C:\Projects\lectio-lesson builder` as the authoritative source for the existing builder implementation, then adapt imports and integration to textbook agent conventions.
- **Risk:** Some source paths or assumptions may differ from the older structure referenced by the guide; integration checks in textbook agent are required to catch drift.
### Decision: Allow adapter bridge to import V3 converter + generation exporter
- **Context:** Phase 1 import rule says builder should avoid imports from `$lib/studio/*` and `$lib/generation/*`, but the phase task explicitly requires composing `adaptV3PackToLectioDocument()` and `exportToLessonDocument()`.
- **Guide says:** Create `src/lib/builder/adapters/from-generation.ts` using those two functions.
- **Chose:** Implemented this bridge only in `src/lib/builder/adapters/from-generation.ts` and kept all other builder files free from direct studio/brief imports.
- **Risk:** This adapter is a controlled coupling point and should remain the only exception; additional cross-imports would violate builder isolation.

### Decision: Use local-install validation flow for unpublished `lectio@0.4.5`
- **Context:** Frontend dependency target is `lectio@0.4.5`, but npm registry does not yet provide that version in this workspace flow.
- **Guide says:** Frontend must align to the new Lectio version and pass `check` + `build`.
- **Chose:** Kept `frontend/package.json` pinned to `0.4.5` and validated by installing local `../../lectio` plus running full frontend checks/build/tests.
- **Risk:** CI or fresh installs without local publish may need explicit local/registry coordination until `0.4.5` is published.

## Phase 2 - Backend Persistence

### Decision: Use server-authoritative lesson IDs and normalize document IDs to server UUID
- **Context:** Phase 1 created purely client-side lesson IDs in IndexedDB. Phase 2 requires server ownership and persistence as source of truth.
- **Guide says:** "POST /builder/lessons -> save to IDB -> navigate" and use server-assigned UUID.
- **Chose:** Backend `POST /api/v1/builder/lessons` always generates the canonical lesson UUID and rewrites `document.id` to match it before persistence/response.
- **Risk:** Older local-only IDB lessons from Phase 1 can exist with non-server IDs and will need migration/recreate flows if reopened.

### Decision: Validate hard integrity only on save; keep pedagogy out of backend blocking rules
- **Context:** Builder is teacher-owned and should not be blocked by pedagogical heuristics, but malformed documents must not be persisted.
- **Guide says:** Block only hard integrity failures (shape, unknown component, bad block refs, payload limits, auth/ownership).
- **Chose:** Added hard validation in backend builder routes for required LessonDocument shape, known `component_id`, section->block reference integrity, and payload size limits.
- **Risk:** Some non-critical content inconsistencies remain possible by design and should surface as UX warnings rather than server rejections.

### Decision: Reuse existing sync-queue primitives with a new builder server-sync adapter
- **Context:** Existing builder persistence already had IndexedDB and a sync queue abstraction, but no server CRUD integration.
- **Guide says:** Keep IDB as offline cache while server remains authoritative; reconnect should sync queued work.
- **Chose:** Implemented `server-sync.ts` to debounce server PUTs, enqueue retryable failures, and register a queue adapter flushed on reconnect/manual save.
- **Risk:** Toolbar save status reflects immediate save attempts; background queue flush success may not instantly update status until next save cycle.
