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
