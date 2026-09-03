"""Production Component Lectio execution (real executors + DB checkpoints).

Do not route live traffic through ``run_mocked_component_lectio_pipeline``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from contracts.lesson_document import assert_valid_lesson_document
from generation.component_lectio.lane_dispatch import (
    WorkOrderIdentityError,
    adapt_answer_key_order,
    adapt_content_order,
    adapt_items_order,
    adapt_visual_order,
    payload_from_answer_key,
    payload_from_component_block,
    payload_from_questions,
    payload_from_visual,
    questions_from_item_payload,
    resolve_exact_order,
    stamp_component_block,
)
from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from v3_blueprint.planning.canonical_plan import (
    SelectorFn,
    build_canonical_execution_plan,
    build_canonical_execution_plan_async,
    heuristic_select_components,
)
from v3_blueprint.planning.component_selector import (
    lesson_context_from_inputs,
    run_lectio_semantic_selector,
)
from v3_blueprint.planning.models import StructuralPlan
from v3_blueprint.planning.persistence import (
    insert_step,
    load_steps,
    persist_chunked_state,
    persist_structural_plan,
    step_exists,
)
from v3_blueprint.planning.work_orders import (
    ExactWorkOrder,
    assert_writer_cannot_change_component,
    compile_exact_work_orders,
)
from v3_execution.executors.answer_key_generator import execute_answer_key
from v3_execution.executors.question_writer import execute_questions
from v3_execution.executors.section_writer import execute_section
from v3_execution.executors.visual_executor import execute_visual
from v3_execution.models import (
    GeneratedAnswerKeyBlock,
    GeneratedComponentBlock,
    GeneratedQuestionBlock,
    GeneratedVisualBlock,
    SectionWriterWorkOrder,
    WriterQuestion,
)
from v3_execution.runtime.failure_policy import (
    BudgetLedger,
    classify_failure,
    recovery_for,
)
from v3_execution.runtime.lesson_document import assemble_lesson_document, lesson_is_partial
from v3_execution.runtime.checkpoints import (
    BlockCheckpoint,
    CheckpointStore,
    GenerationControlState,
)

log = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
SectionExecutorFn = Callable[..., Awaitable[list[GeneratedComponentBlock]]]
QuestionExecutorFn = Callable[..., Awaitable[list[GeneratedQuestionBlock]]]
VisualExecutorFn = Callable[..., Awaitable[list[GeneratedVisualBlock]]]
AnswerKeyExecutorFn = Callable[..., Awaitable[GeneratedAnswerKeyBlock | None]]

READY_STEP = "block_ready"
FAILED_STEP = "block_failed"

DEFAULT_PRODUCTION_SELECTOR = run_lectio_semantic_selector


async def _silent_emit(_event: str, _payload: dict[str, Any]) -> None:
    return None


def adapt_exact_orders_to_section_work_orders(
    orders: list[ExactWorkOrder],
    *,
    plan: StructuralPlan,
    template_id: str,
) -> list[SectionWriterWorkOrder]:
    """Adapt ExactWorkOrders into per-block SectionWriterWorkOrders (content lane)."""
    return [
        adapt_content_order(order, plan=plan, template_id=template_id)
        for order in orders
        if order.lane == "content"
    ]


def _blocks_from_executor(
    generated: list[GeneratedComponentBlock],
    *,
    scoped_orders: list[ExactWorkOrder],
) -> list[tuple[ExactWorkOrder, dict[str, Any]]]:
    results: list[tuple[ExactWorkOrder, dict[str, Any]]] = []
    for block in generated:
        order = resolve_exact_order(block, scoped_orders=scoped_orders)
        stamped = stamp_component_block(block, order)
        assert_writer_cannot_change_component(order, stamped.component_id)
        results.append((order, payload_from_component_block(stamped, order)))
    return results


async def _persist_ready_block(
    generation_id: str,
    *,
    block_id: str,
    payload: dict[str, Any],
    plan_revision: int,
    plan_hash: str,
) -> None:
    if await step_exists(generation_id, part_id=block_id, step=READY_STEP):
        return
    await insert_step(
        generation_id,
        part_id=block_id,
        step=READY_STEP,
        payload={
            "block_id": block_id,
            "plan_revision": plan_revision,
            "plan_hash": plan_hash,
            "payload": payload,
        },
    )


async def _persist_failed_block(
    generation_id: str,
    *,
    order: ExactWorkOrder,
    error: dict[str, Any],
) -> None:
    await insert_step(
        generation_id,
        part_id=order.block_id,
        step=FAILED_STEP,
        payload={"error": error},
    )


async def load_ready_block_ids(generation_id: str) -> set[str]:
    rows = await load_steps(generation_id)
    ready: set[str] = set()
    for row in rows:
        if row.step == READY_STEP:
            ready.add(row.part_id)
    return ready


async def reconstruct_checkpoint_store(
    generation_id: str,
    *,
    plan_revision: int,
    plan_hash: str,
    desired_work: list[str],
) -> CheckpointStore:
    """Rebuild CheckpointStore view from DB generation_steps (durable)."""
    store = CheckpointStore(
        control=GenerationControlState(
            generation_id=generation_id,
            state="running",
            plan_revision=plan_revision,
            plan_hash=plan_hash,
            desired_work=desired_work,
        )
    )
    rows = await load_steps(generation_id)
    for row in rows:
        if row.step == READY_STEP:
            payload = row.payload if isinstance(row.payload, dict) else {}
            inner = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
            store.blocks[row.part_id] = BlockCheckpoint(
                block_id=row.part_id,
                plan_revision=int(payload.get("plan_revision") or plan_revision),
                plan_hash=str(payload.get("plan_hash") or plan_hash),
                state="ready",
                payload=inner if isinstance(inner, dict) else {},
            )
        elif row.step == FAILED_STEP:
            payload = row.payload if isinstance(row.payload, dict) else {}
            store.blocks[row.part_id] = BlockCheckpoint(
                block_id=row.part_id,
                plan_revision=plan_revision,
                plan_hash=plan_hash,
                state="failed",
                last_error=payload.get("error") if isinstance(payload.get("error"), dict) else {
                    "message": str(payload)
                },
            )
    return store


def _structured_error(
    *,
    generation_id: str,
    order: ExactWorkOrder,
    exc: BaseException,
    failure_class: str,
    attempt: int,
) -> dict[str, Any]:
    return {
        "generation_id": generation_id,
        "section_id": order.section_id,
        "block_id": order.block_id,
        "component_id": order.locked_component_id,
        "lane": order.lane,
        "class": failure_class,
        "message": str(exc)[:400],
        "validation_errors": [str(exc)[:400]],
        "attempt": attempt,
    }


async def run_component_lectio_execution(
    *,
    generation_id: str,
    plan: StructuralPlan,
    signals: V3SignalSummary | None = None,
    form: V3InputForm | None = None,
    resource_spec: dict[str, Any] | None = None,
    emit_event: EmitFn | None = None,
    title: str | None = None,
    template_id: str = "guided-concept-path",
    section_executor: SectionExecutorFn | None = None,
    question_executor: QuestionExecutorFn | None = None,
    visual_executor: VisualExecutorFn | None = None,
    answer_key_executor: AnswerKeyExecutorFn | None = None,
    selector: SelectorFn | None = None,
) -> dict[str, Any]:
    """Production entrypoint: semantic selection → lanes → real executors → DB checkpoints."""
    del resource_spec
    execute_content = section_executor or execute_section
    execute_item = question_executor or execute_questions
    execute_vis = visual_executor or execute_visual
    execute_answers = answer_key_executor or execute_answer_key
    emit: EmitFn = emit_event or _silent_emit
    select = selector if selector is not None else DEFAULT_PRODUCTION_SELECTOR
    lesson_context = lesson_context_from_inputs(form=form, signals=signals)

    canonical, filled = await build_canonical_execution_plan_async(
        plan,
        generation_id=generation_id,
        lesson_id=title,
        template_id=template_id,
        selector=select,
        lesson_context=lesson_context,
    )
    await persist_structural_plan(generation_id, filled, form=form)
    await persist_chunked_state(
        generation_id,
        {
            "canonical_plan": canonical.model_dump(mode="json"),
            "structural_plan": filled.model_dump(mode="json"),
            "stage": "component_lectio_running",
            "control_meta": {
                "plan_hash": canonical.plan_hash,
                "plan_revision": canonical.plan_revision,
                "pipeline": "component_lectio",
            },
        },
    )

    orders = compile_exact_work_orders(canonical, include_visual=True)
    desired = [order.block_id for order in orders]
    ready = await load_ready_block_ids(generation_id)
    pending_orders = [order for order in orders if order.block_id not in ready]
    ledgers: dict[str, BudgetLedger] = {}
    item_questions: dict[str, list[WriterQuestion]] = {}
    last_error: str | None = None

    await emit(
        "component_lectio_execution_started",
        {
            "generation_id": generation_id,
            "pending_blocks": [o.block_id for o in pending_orders],
            "ready_blocks": sorted(ready),
        },
    )

    async def dispatch(order: ExactWorkOrder) -> dict[str, Any]:
        if order.lane == "content":
            section_order = adapt_content_order(order, plan=filled, template_id=template_id)
            generated = await execute_content(
                section_order,
                emit,
                trace_id=generation_id,
                generation_id=generation_id,
            )
            mapped = _blocks_from_executor(generated, scoped_orders=[order])
            if not mapped:
                raise WorkOrderIdentityError(
                    f"Content executor returned no matching block for {order.block_id}"
                )
            mapped_order, payload = mapped[0]
            if mapped_order.block_id != order.block_id:
                raise WorkOrderIdentityError(
                    f"Content output claimed {mapped_order.block_id}, expected {order.block_id}"
                )
            return payload
        if order.lane == "items":
            q_order = adapt_items_order(order, plan=filled)
            generated_q = await execute_item(
                q_order,
                emit,
                trace_id=generation_id,
                generation_id=generation_id,
            )
            payload = payload_from_questions(generated_q, order)
            item_questions[order.section_id] = questions_from_item_payload(payload)
            return payload
        if order.lane == "visual":
            v_order = adapt_visual_order(order, plan=filled)
            generated_v = await execute_vis(
                v_order,
                emit,
                trace_id=generation_id,
                generation_id=generation_id,
            )
            if not generated_v:
                raise RuntimeError("visual executor returned no blocks")
            visual = generated_v[0]
            resolved = resolve_exact_order(visual, scoped_orders=[order])
            if resolved.block_id != order.block_id:
                raise WorkOrderIdentityError(
                    f"Visual output claimed {resolved.block_id}, expected {order.block_id}"
                )
            return payload_from_visual(visual, order)
        if order.lane == "answer_key":
            questions = list(item_questions.get(order.section_id) or [])
            if not questions:
                store = await reconstruct_checkpoint_store(
                    generation_id,
                    plan_revision=canonical.plan_revision,
                    plan_hash=canonical.plan_hash,
                    desired_work=desired,
                )
                for sibling in orders:
                    if sibling.lane == "items" and sibling.section_id == order.section_id:
                        ckpt = store.blocks.get(sibling.block_id)
                        if ckpt and ckpt.state == "ready":
                            questions.extend(questions_from_item_payload(ckpt.payload))
            ak_order = adapt_answer_key_order(order, questions=questions)
            generated_ak = await execute_answers(
                ak_order,
                emit,
                trace_id=generation_id,
                generation_id=generation_id,
            )
            if generated_ak is None:
                raise RuntimeError("answer_key executor returned nothing")
            return payload_from_answer_key(generated_ak, order)
        raise RuntimeError(f"Unknown work-order lane: {order.lane}")

    async def execute_one(order: ExactWorkOrder) -> None:
        nonlocal last_error
        if order.block_id in ready:
            return
        ledger = ledgers.setdefault(order.block_id, BudgetLedger())
        attempt = 1
        try:
            payload = await dispatch(order)
            await _persist_ready_block(
                generation_id,
                block_id=order.block_id,
                payload=payload,
                plan_revision=canonical.plan_revision,
                plan_hash=canonical.plan_hash,
            )
            ready.add(order.block_id)
            await emit("block_ready", {"generation_id": generation_id, "block_id": order.block_id})
            return
        except Exception as exc:  # noqa: BLE001
            failure = classify_failure(
                exc,
                block_id=order.block_id,
                kind_hint=order.lane if order.lane == "visual" else None,
            )
            action = recovery_for(failure, ledger, sibling_block_ids=sorted(ready))
            log.warning(
                "component_lectio_block_failure generation_id=%s block=%s class=%s action=%s",
                generation_id,
                order.block_id,
                failure.failure_class.value,
                action.action,
            )
            if action.action in {"retry", "repair"}:
                attempt = 2
                try:
                    payload = await dispatch(order)
                    await _persist_ready_block(
                        generation_id,
                        block_id=order.block_id,
                        payload=payload,
                        plan_revision=canonical.plan_revision,
                        plan_hash=canonical.plan_hash,
                    )
                    ready.add(order.block_id)
                    await emit(
                        "block_ready",
                        {"generation_id": generation_id, "block_id": order.block_id},
                    )
                    return
                except Exception as retry_exc:  # noqa: BLE001
                    exc = retry_exc
                    failure = classify_failure(retry_exc, block_id=order.block_id)
            error = _structured_error(
                generation_id=generation_id,
                order=order,
                exc=exc,
                failure_class=failure.failure_class.value,
                attempt=attempt,
            )
            await _persist_failed_block(generation_id, order=order, error=error)
            last_error = error["message"]

    ordered = [order for order in pending_orders if order.lane != "answer_key"] + [
        order for order in pending_orders if order.lane == "answer_key"
    ]
    for order in ordered:
        await execute_one(order)

    store = await reconstruct_checkpoint_store(
        generation_id,
        plan_revision=canonical.plan_revision,
        plan_hash=canonical.plan_hash,
        desired_work=desired,
    )
    partial = lesson_is_partial(canonical, store)
    document = assemble_lesson_document(
        canonical,
        store,
        title=title or (form.topic if form else "Lesson"),
        subject=form.subject if form else "General",
        template_id=template_id,
        preset_id="default",
    )

    if partial:
        store.mark_terminal("failed")
        await persist_chunked_state(
            generation_id,
            {
                "stage": "assembly_blocked",
                "error": last_error or "Required work remains incomplete",
                "error_type": "ComponentLectioIncomplete",
                "control_meta": {
                    "plan_hash": canonical.plan_hash,
                    "plan_revision": canonical.plan_revision,
                    "pipeline": "component_lectio",
                    "partial": True,
                },
            },
        )
        raise RuntimeError(last_error or "Required Component Lectio work remains incomplete")

    assert_valid_lesson_document(document)
    store.mark_terminal("complete")

    from core.database.models import GenerationModel
    from core.database.session import async_session_factory

    async with async_session_factory() as session:
        model = await session.get(GenerationModel, generation_id)
        if model is not None:
            model.document_json = document
            await session.commit()

    await persist_chunked_state(
        generation_id,
        {
            "stage": "complete",
            "execution_started": True,
            "lesson_document": document,
            "control_meta": {
                "plan_hash": canonical.plan_hash,
                "plan_revision": canonical.plan_revision,
                "pipeline": "component_lectio",
                "partial": False,
            },
        },
    )
    await emit(
        "component_lectio_complete",
        {"generation_id": generation_id, "pipeline": "component_lectio"},
    )
    return document


async def fill_plan_components_for_legacy_studio(
    plan: StructuralPlan,
    *,
    generation_id: str | None = None,
) -> StructuralPlan:
    """Studio rollback bridge: fill empty Stage-1 components via constrained selection."""
    _canonical, filled = build_canonical_execution_plan(
        plan,
        generation_id=generation_id,
        selector=heuristic_select_components,
    )
    return filled
