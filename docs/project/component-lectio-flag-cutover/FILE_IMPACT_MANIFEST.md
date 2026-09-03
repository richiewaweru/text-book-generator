# File Impact Manifest

Casa must inspect the actual branch before editing and keep the changed-file list as small as possible.

## 1. Required / likely backend changes

### `backend/src/core/config.py`

Add typed `GENERATION_PIPELINE_DEFAULT`.

Default: `component_lectio`  
Allowed: `component_lectio`, `v3_studio`

### `backend/src/generation/routes.py`

Current state directly mounts `v3_studio_router`.

Expected role after change:

- continue exposing needed routers;
- mount/route a thin dispatcher or Component Lectio entrypoint if needed;
- do not make raw Studio orchestration the only generation owner.

Do not delete Studio.

### Preferred new dispatch authority

```text
backend/src/generation/pipeline_dispatch.py
```

Possible responsibilities:

```text
GenerationPipeline type
select_default_pipeline()
resolve_generation_pipeline(generation)
persist_pipeline_identity(...)
```

Keep selection logic centralized.

### Component Lectio package

Existing:

```text
backend/src/generation/component_lectio/__init__.py
backend/src/generation/component_lectio/pipeline.py
```

Likely add:

```text
backend/src/generation/component_lectio/service.py
```

Only if needed:

```text
backend/src/generation/component_lectio/routes.py
backend/src/generation/component_lectio/repository.py
```

Do not simply rename the mocked pipeline and call it production.

---

## 2. Existing execution infrastructure to adapt, not replace

Inspect/change only where necessary:

```text
backend/src/v3_blueprint/planning/canonical_plan.py
backend/src/v3_blueprint/planning/work_orders.py

backend/src/v3_execution/runtime/failure_policy.py
backend/src/v3_execution/runtime/lectio_validation.py
backend/src/v3_execution/runtime/runner.py
backend/src/v3_execution/runtime/events.py

backend/src/v3_execution/executors/section_writer.py
backend/src/v3_execution/executors/question_writer.py
backend/src/v3_execution/executors/item_executor.py
backend/src/v3_execution/executors/answer_key_generator.py
backend/src/v3_execution/executors/visual_executor.py
```

Any changes should be compatibility/adaptation changes, not parallel rewrites.

---

## 3. Persistence

Inspect:

```text
backend/src/core/database/models.py
backend/src/v3_blueprint/planning/persistence.py
backend/src/generation/v3_studio/generation_writer.py
```

Reuse durable semantics already present.

Prefer no migration if pipeline identity/control state can safely live in canonical JSON state.

If a migration is truly required, explain why in the completion report.

---

## 4. V3 Studio — keep alive

Do not delete:

```text
backend/src/generation/v3_studio/*
```

Allowed changes:

- narrow wrapper/dispatch integration;
- extracting a reusable legacy service function where essential;
- observability markers.

Avoid broad cleanup.

Legacy must remain runnable with:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

---

## 5. Builder backend

Inspect/preserve:

```text
backend/src/builder/routes.py
backend/src/generation/block_generate.py
backend/src/generation/block_generate_routes.py
```

Preserve editable lessons and AI block assistance.

---

## 6. Frontend likely changes

### `frontend/src/lib/builder/adapters/from-generation.ts`

Target split:

```text
component_lectio → canonical LessonDocument directly
v3_studio        → existing V3 adapter
```

Keep legacy adapter until stability proof.

### `frontend/src/lib/api/v3.ts`

Touch only if required for:

- pipeline metadata;
- Component Lectio response shape;
- routing the generation action through backend dispatch.

Do not split/rename the entire module.

### Preserve generic generation utilities

```text
frontend/src/lib/generation/generation-poller.ts
frontend/src/lib/generation/live-stream.ts
frontend/src/lib/builder/streaming/generation-stream.ts
```

Adapt only if required.

---

## 7. Tests to add

Recommended focused suite:

```text
backend/tests/generation/test_pipeline_flag.py
backend/tests/generation/test_pipeline_persistence.py
backend/tests/generation/test_pipeline_dispatch.py
backend/tests/generation/test_component_lectio_live_entrypoint.py
backend/tests/generation/test_no_automatic_legacy_fallback.py
backend/tests/generation/test_historical_pipeline_inference.py
backend/tests/generation/test_component_lectio_resume.py
backend/tests/generation/test_component_lectio_builder_contract.py
```

Frontend test if ingestion changes:

```text
frontend/src/lib/builder/adapters/from-generation.test.ts
```

Use repository conventions if test paths differ.

---

## 8. Explicitly do not delete

```text
backend/src/generation/v3_studio/*
frontend/src/lib/studio/*
frontend/src/lib/components/studio/*
frontend/src/lib/api/v3.ts
backend/src/v3_execution/*
backend/src/v3_blueprint/*
frontend/src/lib/builder/*
frontend/src/routes/builder/*
backend/src/generation/block_generate*.py
```

---

## 9. Environment configuration

Document:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

Do not commit secrets.

If Vercel configuration is external, report the exact environment variable to set.

---

## 10. Final changed-file discipline

Completion report must list:

```text
CREATED
MODIFIED
DELETED
```

Expected:

```text
DELETED: none
```
