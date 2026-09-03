# Implementation Contract

## A. Scope

Implement the minimum production wiring required to make Component Lectio the default generation pipeline behind an explicit runtime feature flag.

Do not delete legacy code. Do not redesign Component Lectio. Do not run the later four-subject Codex live verification. Do not hide failures by falling back to V3 Studio.

---

## B. Feature flag

Prefer an enum-like setting:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

Allowed values:

```text
component_lectio
v3_studio
```

Recommended typed shape:

```python
GenerationPipeline = Literal["component_lectio", "v3_studio"]
generation_pipeline_default: GenerationPipeline = "component_lectio"
```

Reject unknown values at startup.

Repository/application default must be `component_lectio`.

Rollback is performed by setting:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

and redeploying/restarting.

---

## C. Dispatch law

The flag chooses the pipeline once, at generation admission:

```text
new generation request
        ↓
read GENERATION_PIPELINE_DEFAULT
        ↓
persist selected pipeline on generation
        ↓
execute that pipeline for the lifetime of that generation
```

After creation, status/retry/resume must not use the current global flag.

Example:

```text
Generation A created with component_lectio
operator changes default to v3_studio
Generation A retry requested
```

A must remain Component Lectio. A later Generation B may use Studio.

---

## D. Persist pipeline identity

Use an existing durable generation JSON field unless a migration is demonstrably necessary.

Preferred canonical location:

```text
GenerationModel.chunked_state_json.control.pipeline
```

or another single generation-control location already used by the runtime.

Persist at minimum:

```json
{
  "pipeline": "component_lectio",
  "pipeline_version": 1,
  "selected_at": "<UTC ISO timestamp>"
}
```

Do not create multiple competing authorities.

Historical rows without a marker may be inferred as `v3_studio`, with explicit inference logging.

---

## E. Observability

Every generation must expose evidence for the next Codex verification phase.

At minimum:

### Persisted state

```text
pipeline=component_lectio
```

### Structured log/event

```json
{
  "event": "generation_pipeline_selected",
  "generation_id": "...",
  "pipeline": "component_lectio"
}
```

### Status/detail API

Expose `pipeline` where compatible.

### Optional debug header

```text
X-Generation-Pipeline: component_lectio
```

The header is supplemental, never authoritative.

---

## F. No silent fallback

Never implement:

```python
try:
    run_component_lectio()
except Exception:
    return run_v3_studio()
```

Expected behavior:

```text
Component Lectio selected
        ↓
Component Lectio fails
        ↓
record Component Lectio failure
        ↓
surface retryable or terminal state
```

Rollback is an operator action through the environment setting.

---

## G. Production Component Lectio entrypoint

Do not use `run_mocked_component_lectio_pipeline` for live traffic.

Create or promote a production-oriented entrypoint under the existing Component Lectio package, for example:

```text
backend/src/generation/component_lectio/service.py
```

Expected flow:

```text
approved lesson / IntentPlan
        ↓
intent_plan_to_structural_plan
        ↓
build_canonical_execution_plan
        ↓
compile_exact_work_orders
        ↓
real executor dispatch
        ├── section/content writer
        ├── item/question writer
        └── visual executor
        ↓
Lectio validation
        ↓
typed retry / scoped repair
        ↓
database checkpoint persistence
        ↓
partial/final LessonDocument
        ↓
status/events
```

Keep the mocked pipeline as deterministic test scaffolding if useful.

---

## H. Reuse real executors

Reuse existing code where applicable:

```text
backend/src/v3_execution/executors/section_writer.py
backend/src/v3_execution/executors/question_writer.py
backend/src/v3_execution/executors/item_executor.py
backend/src/v3_execution/executors/answer_key_generator.py
backend/src/v3_execution/executors/visual_executor.py
backend/src/v3_execution/runtime/runner.py
backend/src/v3_execution/runtime/lectio_validation.py
backend/src/v3_execution/runtime/failure_policy.py
```

Adapt work-order translation at a narrow boundary if needed.

The locked identity must survive translation:

```text
block_id
component_id
section_id
purpose / instructional intent
contract
position
dependencies
```

The writer fills the chosen contract; it does not choose another component.

---

## I. Durable checkpoints

The in-memory `CheckpointStore` is test scaffolding, not the live control plane.

Production Component Lectio must checkpoint through the database.

Reuse existing append-only `GenerationStepModel` / `chunked_state_json` semantics.

Required properties:

- stable block ID is the idempotency identity;
- ready blocks are not regenerated on resume unless explicitly invalidated;
- block failure is persisted;
- retry/repair attempts are persisted;
- terminal generation state is persisted;
- process/service object recreation does not erase progress.

If a generic runtime repository already exists, use it rather than create another persistence layer.

---

## J. Leases / execution ownership

Do not claim production lease safety using only the current in-process `LeaseStore`.

For a Vercel/distributed path, use persistent/atomic ownership if the repository already supports it.

If durable ownership cannot be safely completed without a larger infrastructure change:

1. implement the flag/routing and real execution wiring that is safely possible;
2. mark durable lease support as `BLOCKED / NOT YET PRODUCTION-SAFE`;
3. do not mislabel the in-memory model as complete.

Do not add Redis or speculative new infrastructure unless clearly necessary.

---

## K. Public route strategy

Minimize frontend churn.

A current V3-named endpoint may temporarily remain the public surface if it dispatches through a thin pipeline authority.

Recommended architecture:

```text
existing request endpoint
        ↓
thin generation dispatcher
        ↓
persisted pipeline
        ├── component_lectio service
        └── v3_studio legacy service
```

Avoid duplicating the giant V3 Studio router.

Shared pre-generation functions such as signal extraction/topic narrowing may remain temporarily if they are not the generation execution owner.

Document the exact branch point.

---

## L. Builder contract

Target Component Lectio:

```text
Component Lectio
        ↓
canonical LessonDocument
        ↓
Builder
```

Do not convert Component Lectio into a V3 pack merely so it can be converted back to LessonDocument.

During transition:

```text
component_lectio → LessonDocument directly
v3_studio        → V3 pack → existing adapter
```

Use explicit pipeline identity rather than guessing from object shape.

Do not delete the Studio adapter.

---

## M. Streaming

Preserve existing generic browser machinery where possible:

```text
frontend/src/lib/generation/generation-poller.ts
frontend/src/lib/generation/live-stream.ts
frontend/src/lib/builder/streaming/generation-stream.ts
```

Component Lectio should expose persisted partial/final state that survives reconnect.

If true partial Builder streaming cannot be completed in this narrow task, report it as a blocker rather than fake it.

---

## N. Existing-generation operations

Any operation targeting an existing generation must dispatch by persisted pipeline, including at least:

```text
status/detail
retry
resume
visual regeneration if pipeline-owned
component repair if pipeline-owned
```

Pseudo-code:

```python
generation = load_generation(id)
pipeline = resolve_persisted_pipeline(generation)

if pipeline == "component_lectio":
    ...
elif pipeline == "v3_studio":
    ...
```

---

## O. Historical generations

Resolution rule:

```text
pipeline field present
→ trust persisted field

pipeline missing on pre-cutover generation
→ infer v3_studio
```

Log inference explicitly.

New generations must never omit pipeline identity.

---

## P. Explicit out of scope

Do not:

- delete `generation/v3_studio`;
- remove Studio frontend files;
- retire `frontend/src/lib/api/v3.ts`;
- rename all V3 endpoints;
- run broad UI redesign;
- perform production cleanup;
- run the four-subject Codex validation matrix;
- optimize latency before functionality is proven;
- add speculative infrastructure.
