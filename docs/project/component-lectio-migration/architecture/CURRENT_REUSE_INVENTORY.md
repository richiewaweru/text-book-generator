# Current Reuse Inventory
Phase 00 must verify against the local checkout.

## Planning/specs — reuse
- `backend/resources/specs/lesson.yaml`: already general lesson arc + constrained component lists.
- `backend/src/resource_specs/schema.py`: role/intent/preferred/allowed/forbidden and allowed/forbidden helpers.
- `backend/resources/component-selector-v1.txt`: already fixed slot purpose + allowed candidates + `cognitive_job` matching + restraint/budget rules.

## Planning — adapt
- `v3_blueprint/planning/structural_planner.py`: currently receives resource spec plus planner index; simplify toward intent/role planning.
- `v3_blueprint/planning/models.py`: reuse LessonIntent, cards, learner/voice context and useful section fields; clarify ownership instead of wholesale replacement.
- `v3_blueprint/planning/section_expander.py`: already loads only selected cards; reuse its narrowing pattern.

## Lectio boundary — reuse
- `backend/src/contracts/lectio.py`: deterministic app↔Lectio boundary.
- `backend/src/v3_execution/runtime/lectio_validation.py`: exact field and SectionContent validation; extend coverage instead of replacing.

## Execution — reuse/adapt
- `v3_execution/runtime/runner.py`, `lanes.py`, events and executors: preserve concurrency/streaming concepts; refactor around durable checkpoints/work orders.
- execution config/timeouts/retries: centralize new typed failure policy around existing config.

## Persistence — reuse
- `v3_blueprint/planning/persistence.py`: immutable generation-step pattern; do not regress to concurrent mutable blobs.
- `GenerationModel.chunked_state_json`: broad control state.
- `GenerationStepModel`: append-only completed work/checkpoints.

## Builder/frontend — preserve
- generic generation poller;
- live stream reconciliation;
- Builder generation-stream partial merge (move toward stable block IDs);
- Builder persistence/sync/document stores;
- block-generation assistance;
- visual regeneration;
- PDF/rendering infrastructure.

## Mine then remove
- `generation/v3_studio/generation_writer.py`: mine status/snapshot/error persistence.
- `generation/v3_studio/router.py`: mine active API behavior, telemetry, visual/repair/status responsibilities, then split them.
- V3 pack→Lectio Builder adapter: remove after direct LessonDocument path is proven.
