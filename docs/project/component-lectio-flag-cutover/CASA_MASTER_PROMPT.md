# CASA MASTER PROMPT — Make Component Lectio the Default Flagged Path

Work in:

```text
repository: richiewaweru/text-book-generator
branch: xplore
```

Read every file in this handoff package before changing code.

Your task is deliberately narrow:

> Make the new Component Lectio generation path the default production path behind a runtime feature flag, preserve V3 Studio as an explicit rollback path, and leave the branch ready for inspection before a separate Codex live end-to-end verification.

Do not delete legacy Studio code.  
Do not conduct the later full live/browser test.  
Do not redesign the educational architecture.

## 1. Preserve the working tree

Inspect:

```text
git status
current branch
current commit
```

Preserve all pre-existing dirty changes.

Do not reset, clean, destructively stash, or overwrite unrelated work.

Record starting state in the completion report.

## 2. Re-inspect the branch

The handoff snapshot showed:

- `backend/src/generation/routes.py` still mounting `generation.v3_studio.router`;
- `backend/src/generation/component_lectio/pipeline.py` explicitly using mocked writers;
- `v3_execution/runtime/checkpoints.py` and `leases.py` as in-memory stand-ins;
- Builder still using `studio/v3-pack-to-lectio-document`.

Re-check first. If the branch evolved, adapt to actual code while preserving the invariants below.

## 3. Implement one typed runtime flag

Use:

```text
GENERATION_PIPELINE_DEFAULT
```

Allowed:

```text
component_lectio
v3_studio
```

Default:

```text
component_lectio
```

Put it in the existing typed configuration system and reject invalid values.

Do not scatter raw environment checks.

## 4. Select once, persist forever for that generation

At new-generation admission:

```text
read default
↓
select pipeline
↓
persist pipeline identity
↓
execute selected pipeline
```

After that, status/retry/resume uses the persisted pipeline.

Changing environment later affects only new generations.

Historical generations without a marker may be inferred as `v3_studio`, with explicit inference logging.

## 5. No automatic fallback

Never do:

```text
Component Lectio error
→ silently run V3 Studio
```

A Component Lectio failure stays a Component Lectio failure.

Rollback is operational:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

The next verification phase must be able to see instability rather than have it hidden.

## 6. Wire a real Component Lectio production entrypoint

Do NOT expose `run_mocked_component_lectio_pipeline` to production traffic.

Retain it as deterministic test scaffolding if useful.

Create/promote a production service that reuses the implemented architecture:

```text
IntentPlan
↓
canonical Component Lectio plan
↓
exact work orders
↓
existing real executors
↓
Lectio validation
↓
typed retry / scoped repair
↓
database checkpoints
↓
LessonDocument
```

Reuse the existing section/question/item/answer/visual executors and runtime.

Do not create duplicate writers, component registries, or schemas.

## 7. Use a thin dispatch seam

Avoid duplicating the giant V3 Studio router.

Create one clear pipeline-dispatch authority that knows:

```text
new generation default
existing generation persisted pipeline
historical legacy inference
```

Current V3-named frontend URLs may temporarily remain if changing them broadens scope.

Execution cutover matters more than naming cleanup.

Document the exact branch point.

## 8. Make persistence honest

The current proof `CheckpointStore`/`LeaseStore` must not be mistaken for production durability.

Use existing DB generation/checkpoint semantics where available:

```text
GenerationModel
GenerationStepModel
chunked_state_json
existing persistence fold/insert helpers
```

Persist pipeline identity and sufficient runtime state to survive object/process recreation.

If durable worker ownership cannot be safely completed without larger infrastructure, do not fake it. Mark it as a blocker.

## 9. Keep Builder compatible

Expected transition:

```text
component_lectio
→ canonical LessonDocument
→ Builder directly

v3_studio
→ V3 pack
→ existing Studio adapter
→ Builder
```

Do not delete the legacy adapter.

Use explicit pipeline identity to select ingestion path rather than guessing from shape.

Preserve Builder save/edit/block-generation behavior.

## 10. Preserve streaming/retry infrastructure

Do not rewrite generic polling, SSE, executor concurrency, or visuals unless required.

Reuse:

```text
generation poller
live stream
Builder generation stream
existing execution runner
visual executor
failure policy
```

If partial Component Lectio streaming remains incomplete, report it rather than pretend it works.

## 11. Add observability for the next verification phase

Every new generation must make the actual pipeline provable.

At minimum:

```text
persisted pipeline marker
status/detail API pipeline field
structured pipeline-selection log/event
```

Optional:

```text
X-Generation-Pipeline
```

Include pipeline in relevant retry/failure logs.

Never log secrets.

## 12. Tests

Implement and run `ACCEPTANCE_TESTS.md`.

Most importantly prove:

```text
default → component_lectio
explicit rollback → v3_studio
generation keeps original pipeline after flag changes
Component Lectio failure does not fallback
live Component Lectio does not use mock_writer
pipeline marker persists
historical unmarked generation resolves to legacy
Builder can ingest Component Lectio directly
legacy Builder adapter still works
```

Run existing repository lint/type/test/build commands too.

## 13. No deletion

Do not delete:

```text
backend/src/generation/v3_studio/*
frontend/src/lib/studio/*
frontend/src/lib/components/studio/*
frontend/src/lib/api/v3.ts
```

or other legacy paths in this phase.

## 14. Keep scope disciplined

Do not:

- redesign UI;
- rename every endpoint;
- optimize latency;
- perform broad refactors;
- add speculative queue infrastructure;
- port page-oriented semantics;
- change intent/component-selection philosophy;
- run the four-subject live verification.

If a blocker exists, solve the smallest code problem needed or report it.

## 15. Completion report

Return a Markdown report using:

```text
POST_IMPLEMENTATION_REPORT_TEMPLATE.md
```

Also include a concise diff summary and exact commands/tests run.

Final verdict must be exactly one of:

```text
READY FOR INSPECTION
PARTIALLY READY — BLOCKERS REMAIN
BLOCKED
```

`READY FOR INSPECTION` means the cutover wiring is credible enough for us to inspect. It does not mean live production stability is proven.
