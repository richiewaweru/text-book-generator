# Current `xplore` Branch Findings

Repository: `richiewaweru/text-book-generator`  
Branch: `xplore`

Re-inspect these before editing in case the branch has moved.

## 1. Live backend routing still mounts Studio

`backend/src/generation/routes.py` currently imports and mounts:

```python
from generation.v3_studio.router import v3_studio_router

router = APIRouter(prefix="/api/v1", tags=["generation"])
router.include_router(v3_studio_router)
router.include_router(block_generate_router)
```

So live generation traffic can still be owned by V3 Studio.

## 2. Component Lectio top-level pipeline is still a mocked proof path

`backend/src/generation/component_lectio/pipeline.py` currently declares:

```python
"""Canonical Component Lectio pipeline (mocked writers) — Phases 09/10 path."""
```

and exposes `run_mocked_component_lectio_pipeline(...)` with `mock_writer(...)`.

Do not route live production traffic directly into this mocked proof function.

## 3. Checkpoint helper is not yet durable storage

`backend/src/v3_execution/runtime/checkpoints.py` says:

```python
class CheckpointStore:
    """In-memory stand-in mirroring append-only generation_steps fold semantics."""
```

The production path must persist through existing DB structures / `GenerationStepModel` semantics.

## 4. Lease helper is also an in-process model

`backend/src/v3_execution/runtime/leases.py` says:

```python
"""DB-shaped worker leases / fencing (Phase 07). Minimal in-process model of durable claims."""
```

Do not present this as a production DB lease until backed by persistent/atomic ownership.

## 5. Builder still depends on Studio conversion

`frontend/src/lib/builder/adapters/from-generation.ts` imports `adaptV3PackToLectioDocument` from:

```text
$lib/studio/v3-pack-to-lectio-document
```

Target Component Lectio should expose/consume the canonical Builder-compatible `LessonDocument` directly. Legacy V3 generations may continue using the adapter during this phase.

## 6. Frontend generation API remains V3-namespaced

`frontend/src/lib/api/v3.ts` still calls routes such as:

```text
/api/v1/v3/signals
/api/v1/v3/propose-intent
/api/v1/v3/chunked/plan/start
/api/v1/v3/chunked/{generation_id}/approve
```

Do not perform a broad API rename in this task. A V3-named URL may temporarily dispatch to Component Lectio; URL naming is not the same as runtime ownership.

## 7. Existing infrastructure to reuse

Do not rebuild unless a concrete defect requires it:

- `v3_blueprint` canonical plan/work-order machinery.
- real section/question/item/answer/visual executors.
- existing runtime concurrency/streaming runner.
- `GenerationModel` and `GenerationStepModel`.
- existing `chunked_state_json` / append-only persistence patterns.
- Builder polling and live-stream utilities.
- Builder block-generation/AI-assist routes.
- PDF infrastructure.
- visual executor.

## Target outcome

With:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

a normal UI generation should execute Component Lectio.

With:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

new generations should use the old path without code edits.

The branch must then be credible enough for the next separate Codex full-computer-use live test.
