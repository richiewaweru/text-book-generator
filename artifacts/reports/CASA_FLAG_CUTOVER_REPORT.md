# Casa Flag Cutover Report — Component Lectio

## 1. Verdict

```text
PARTIALLY READY — BLOCKERS REMAIN
```

Flag default, dispatch, production Component Lectio entrypoint (real executors), DB checkpoints, no silent Studio fallback, and Builder pipeline split are in place and covered by targeted tests. Residual P1: process leases remain in-memory (`LeaseStore`), not DB-backed — not claimed production-safe.

## 2. Repository identity

```text
repo: Textbook agent
branch: xplore
starting commit: e552e604d4056bb13c6d70a56f710862f2b1b7e3
ending commit: e552e604d4056bb13c6d70a56f710862f2b1b7e3 (Casa changes uncommitted)
dirty state before: prior migration tree + in-progress Casa work
dirty state after: Casa flag-cutover files added/modified (see §13); Studio not deleted
```

## 3. Feature flag

```text
setting name: generation_pipeline_default
env: GENERATION_PIPELINE_DEFAULT
allowed values: component_lectio | v3_studio
default: component_lectio
Vercel value required: optional; omit for Lectio default, set v3_studio to roll back
startup validation: yes — invalid values raise at Settings load
```

```python
GenerationPipeline = Literal["component_lectio", "v3_studio"]
generation_pipeline_default: GenerationPipeline = Field(
    default="component_lectio",
    validation_alias=AliasChoices(
        "GENERATION_PIPELINE_DEFAULT",
        "generation_pipeline_default",
    ),
)
```

## 4. Dispatch boundary

```text
POST /api/v1/v3/chunked/plan/start
↓
select_default_pipeline()  [generation/pipeline_dispatch.py]
↓
persist_pipeline_identity → chunked_state_json.control
↓
Stage 1 (shared IntentPlan)
↓
POST .../approve
↓
resolve_generation_pipeline(persisted state)
├ component_lectio → _run_component_lectio_pipeline → run_component_lectio_execution
└ v3_studio → fill empty components → _run_chunked_stage2_pipeline (legacy)
```

Status / retry-section / approve resume all use `resolve_generation_pipeline` on persisted control (env default ignored after admission).

## 5. Persistence

Pipeline identity lives in `generations.chunked_state_json.control`:

```json
{
  "control": {
    "pipeline": "component_lectio",
    "pipeline_version": 1,
    "selected_at": "2026-09-03T..."
  }
}
```

Historical unmarked rows → `resolve_generation_pipeline` returns `v3_studio` and logs `generation_pipeline_inferred` (`reason=missing_marker`).

## 6. Component Lectio production entrypoint

```text
generation.component_lectio.service.run_component_lectio_execution
```

Proof:

```text
does not call mock_writer
does not call run_mocked_component_lectio_pipeline
uses real execution infrastructure
```

Real executor used in production path: `v3_execution.executors.section_writer.execute_section` (injectable `section_executor` for tests). Flow: canonical plan → ExactWorkOrder → SectionWriterWorkOrder adapter → executor → `insert_step` ready/failed → `assemble_lesson_document` → `document_json` + chunked state.

Mock pipeline retained under `component_lectio/pipeline.py` for unit/E2E mocks only.

## 7. Durable checkpoint / execution ownership

```text
checkpoint persistence: DB-backed (GenerationStepModel via insert_step / reconstruct_checkpoint_store)
lease/ownership: not DB-backed (in-process LeaseStore / process task map)
resume after process restart: ready blocks skip proven via DB reload tests; cross-process exclusive ownership not proven
```

## 8. Builder contract

```text
component_lectio path → generationToBuilderDocument → LessonDocument direct (no adaptV3PackToLectioDocument)
v3_studio path        → generationToBuilderDocument → v3PackToBuilderDocument → adaptV3PackToLectioDocument
```

Builder page hydrates with `pipeline: status.pipeline`.

## 9. No-fallback proof

`test_gate4_no_automatic_legacy_fallback_on_lectio_failure`: monkeypatches `run_component_lectio_execution` to raise; spies `_run_chunked_stage2_pipeline`; asserts studio call count `0` and stage `assembly_blocked` with Lectio pipeline marker retained.

## 10. Retry/status binding

After env flip, `resolve_generation_pipeline(load_chunked_state(...))` trusts `control.pipeline`. Covered by gate 3 (immutable A) and gate 9 (status DTO).

Endpoints/functions:

- `get_chunked_plan_status` (+ optional `X-Generation-Pipeline` header)
- `_normalize_chunked_state` / `_normalize_chunked_status`
- `post_chunked_plan_approve`
- `post_chunked_retry_section` (Lectio → resume Lectio; Studio → section retry)

## 11. Observability

```text
persisted marker: chunked_state_json.control.pipeline
status/detail field: V3ChunkedStatusDTO.pipeline / V3ChunkedPlanStateDTO.pipeline
structured log/event: generation_pipeline_selected / generation_pipeline_inferred
optional response header: X-Generation-Pipeline on status GET
```

## 12. Tests executed

| Command/test | Result | Notes |
|---|---|---|
| `uv run pytest tests/generation/test_pipeline_flag_cutover.py -q` | PASS | 13 gates (default, rollback, sticky, no-fallback, real executor, identity, DB checkpoint, resume, marker, historical, invalid config, Studio present, no mock import) |
| `npm test -- src/lib/builder/adapters/from-generation.test.ts` | PASS | Lectio direct + Studio adapter |
| Codex live four-subject run | NOT RUN | Explicitly out of scope |

## 13. Files changed

### Created

```text
docs/project/component-lectio-flag-cutover/*
backend/src/generation/pipeline_dispatch.py
backend/src/generation/component_lectio/service.py
backend/tests/generation/test_pipeline_flag_cutover.py
artifacts/reports/CASA_FLAG_CUTOVER_REPORT.md
```

### Modified

```text
backend/src/core/config.py
backend/src/generation/component_lectio/__init__.py
backend/src/generation/v3_studio/dtos.py
backend/src/generation/v3_studio/router.py
frontend/src/lib/builder/adapters/from-generation.ts
frontend/src/lib/builder/adapters/from-generation.test.ts
frontend/src/lib/types/v3.ts
frontend/src/routes/builder/[id]/+page.svelte
```

### Deleted

```text
none
```

## 14. Remaining blockers before Codex live run

```text
P1 — lease/ownership: not DB-backed (in-memory LeaseStore). Multi-worker / crash ownership not production-safe.
P2 — visual lane still excluded from generic section writer in this cutover adapter.
P2 — full frontend lint/typecheck/production build not re-run in this session (targeted adapter test only).
```

No P0 found for: mocked live path, unreachable Lectio UI route, missing pipeline marker, or silent Studio fallback.

## 15. Legacy path status

```text
V3 Studio still present: yes
legacy rollback tested: yes (settings + sticky + approve Studio bridge fills components)
no deletion performed: yes
```

## 16. Operator instructions

New-path default:

```text
GENERATION_PIPELINE_DEFAULT=component_lectio
```

Rollback:

```text
GENERATION_PIPELINE_DEFAULT=v3_studio
```

Requires process restart / redeploy so Settings reload. Existing generations keep their persisted pipeline.

## 17. Recommended next action

Do not run Codex live verification from this agent. Branch is suitable for inspection of flag/dispatch/real entrypoint; address DB lease durability before treating multi-instance production ownership as solved.
