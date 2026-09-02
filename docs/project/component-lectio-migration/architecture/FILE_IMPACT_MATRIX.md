# Expected File Impact Matrix
Phase 00 must confirm exact local paths.

## Likely modify
### Specs/planning
- `backend/resources/specs/lesson.yaml`
- `backend/src/resource_specs/{schema,loader,renderer}.py`
- `backend/src/v3_blueprint/planning/{models,structural_planner,validators,assembler,section_expander,persistence,retry}.py`
- planning prompts under `backend/resources/prompts/`
- `backend/resources/component-selector-v1.txt`

### Contracts/execution
- `backend/src/contracts/lectio.py` only for helper/coverage improvements
- `backend/src/v3_execution/runtime/{runner,retry_runner,events,lectio_validation}.py`
- `backend/src/v3_execution/{compile_orders,models}.py`
- existing executors/prompts/config under `v3_execution/`

### API/core
- `backend/src/generation/routes.py`
- `backend/src/app.py`
- DB models only if minimal additive state fields are proven necessary
- `core/llm/runner.py` only if typed provider failure exposure is needed

### Frontend
- `frontend/src/lib/api/v3.ts` during migration, then retire/split
- `frontend/src/lib/generation/live-stream.ts`
- `frontend/src/lib/builder/streaming/generation-stream.ts`
- `frontend/src/lib/builder/adapters/from-generation.ts`
- Builder store/sync files only where revision fencing/live placeholders require it
- relevant unit/generation pages

## Likely create (unless an existing module already owns this responsibility)
- `backend/src/v3_blueprint/planning/canonical_plan.py`
- `backend/src/v3_blueprint/planning/component_selector.py`
- `backend/src/v3_execution/runtime/failure_policy.py`
- `backend/src/v3_execution/runtime/execution_state.py`
- `backend/src/v3_execution/runtime/repository.py`
- `backend/src/v3_execution/runtime/repair.py`
- `backend/src/v3_execution/runtime/worker.py`
- focused generation API module(s) if needed
- phase-specific test suites

## Delete only Phase 09 after gates
- `backend/src/generation/v3_studio/*`
- obsolete Studio frontend routes/components/store
- V3 pack→Lectio Builder conversion adapter
- legacy unit route if unused
- old prompts/resources with zero production callers
- direct non-lesson primary-generation UI/API path

## Do not delete
Builder, generic polling/streaming, visual executor/regeneration, block generation assistance, PDF infrastructure, `GenerationStepModel`, useful concurrency lanes, contract update tooling.
