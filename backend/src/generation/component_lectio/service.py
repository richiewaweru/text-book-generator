"""Production Component Lectio execution (real executors + DB checkpoints).

Do not route live traffic through ``run_mocked_component_lectio_pipeline``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from contracts.lectio import get_component_card
from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from v3_blueprint.planning.canonical_plan import (
    build_canonical_execution_plan,
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
from v3_execution.executors.section_writer import execute_section
from v3_execution.models import (
    GeneratedComponentBlock,
    RegisterSpec,
    SectionWriterWorkOrder,
    SourceOfTruthEntry,
    WriterMisconception,
    WriterSection,
    WriterSectionComponent,
)
from v3_execution.runtime.failure_policy import (
    BudgetLedger,
    classify_failure,
    recovery_for,
)
from v3_execution.runtime.lesson_document import assemble_lesson_document
from v3_execution.runtime.checkpoints import (
    BlockCheckpoint,
    CheckpointStore,
    GenerationControlState,
)

log = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
SectionExecutorFn = Callable[..., Awaitable[list[GeneratedComponentBlock]]]

READY_STEP = "block_ready"
FAILED_STEP = "block_failed"


async def _silent_emit(_event: str, _payload: dict[str, Any]) -> None:
    return None


def adapt_exact_orders_to_section_work_orders(
    orders: list[ExactWorkOrder],
    *,
    plan: StructuralPlan,
    template_id: str,
) -> list[SectionWriterWorkOrder]:
    """Group content-lane ExactWorkOrders into SectionWriterWorkOrders.

    Preserves locked component identity; writers must not change component_id.
    Items/visual lanes are left for dedicated executors (content lane only here).
    """
    by_section: dict[str, list[ExactWorkOrder]] = {}
    for order in orders:
        if order.lane not in {"content", "items", "answer_key"}:
            continue
        # Content + items currently share section writer for this cutover;
        # visual stays out of generic text writer.
        if order.lane == "visual":
            continue
        by_section.setdefault(order.section_id, []).append(order)

    section_meta = {section.id: section for section in plan.sections}
    card_by_id = {card.id: card for card in plan.cards}
    work_orders: list[SectionWriterWorkOrder] = []

    for section_id, section_orders in by_section.items():
        meta = section_meta.get(section_id)
        components: list[WriterSectionComponent] = []
        cards: dict[str, Any] = {}
        for order in section_orders:
            assert_writer_cannot_change_component(order, order.component_id)
            components.append(
                WriterSectionComponent(
                    component_id=order.locked_component_id,
                    teacher_label=order.locked_component_id,
                    content_intent=order.purpose,
                )
            )
            card = get_component_card(order.component_id) or dict(order.component_card)
            cards[order.component_id] = card

        misconceptions = []
        if meta and meta.card_id and meta.card_id in card_by_id:
            for item in card_by_id[meta.card_id].misconceptions:
                misconceptions.append(
                    WriterMisconception(id=item.id, description=item.description)
                )

        work_orders.append(
            SectionWriterWorkOrder(
                work_order_id=f"section::{section_id}",
                section=WriterSection(
                    id=section_id,
                    title=meta.title if meta else section_id,
                    learning_intent=meta.purpose if meta else "",
                    role=meta.role if meta else "",
                    transition_note=meta.transition_note if meta else None,
                    card_id=meta.card_id if meta else None,
                    anchor_example=plan.anchor.example,
                    anchor_reuse_scope=plan.anchor.reuse_scope,
                    misconceptions=misconceptions,
                    components=components,
                ),
                register_spec=RegisterSpec(),
                source_of_truth=[
                    SourceOfTruthEntry(key="anchor", text=plan.anchor.example),
                ],
                component_cards=cards,
                template_id=template_id,
            )
        )
    return work_orders


def _blocks_from_executor(
    generated: list[GeneratedComponentBlock],
    *,
    orders_by_component: dict[str, ExactWorkOrder],
) -> list[tuple[ExactWorkOrder, dict[str, Any]]]:
    results: list[tuple[ExactWorkOrder, dict[str, Any]]] = []
    for block in generated:
        order = orders_by_component.get(block.component_id)
        if order is None:
            continue
        if block.component_id != order.locked_component_id:
            raise ValueError(
                f"Writer attempted to change component_id from "
                f"'{order.locked_component_id}' to '{block.component_id}'"
            )
        results.append(
            (
                order,
                {
                    "content": block.data,
                    "component_id": block.component_id,
                    "section_field": block.section_field,
                    "position": block.position,
                    "block_id": order.block_id,
                },
            )
        )
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
) -> dict[str, Any]:
    """Production entrypoint: selection → work orders → real executors → DB checkpoints."""
    del signals, resource_spec  # reserved for future SoT enrichment
    execute = section_executor or execute_section
    emit: EmitFn = emit_event or _silent_emit

    canonical, filled = build_canonical_execution_plan(
        plan,
        generation_id=generation_id,
        lesson_id=title,
        template_id=template_id,
    )
    await persist_structural_plan(
        generation_id,
        filled,
        form=form,
    )
    await persist_chunked_state(
        generation_id,
        {
            "canonical_plan": canonical.model_dump(mode="json"),
            "structural_plan": filled.model_dump(mode="json"),
            "stage": "component_lectio_running",
        },
    )

    orders = compile_exact_work_orders(canonical, include_visual=False)
    desired = [order.block_id for order in orders]
    ready = await load_ready_block_ids(generation_id)
    pending_orders = [order for order in orders if order.block_id not in ready]

    await emit(
        "component_lectio_execution_started",
        {
            "generation_id": generation_id,
            "pending_blocks": [o.block_id for o in pending_orders],
            "ready_blocks": sorted(ready),
        },
    )

    section_orders = adapt_exact_orders_to_section_work_orders(
        pending_orders,
        plan=filled,
        template_id=template_id,
    )
    orders_by_component = {order.component_id: order for order in pending_orders}
    ledger = BudgetLedger()

    for section_order in section_orders:
        section_pending = [
            c.component_id
            for c in section_order.section.components
            if orders_by_component.get(c.component_id)
            and orders_by_component[c.component_id].block_id not in ready
        ]
        if not section_pending:
            continue
        try:
            generated = await execute(
                section_order,
                emit,
                trace_id=generation_id,
                generation_id=generation_id,
            )
            for order, payload in _blocks_from_executor(
                generated,
                orders_by_component=orders_by_component,
            ):
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
        except Exception as exc:  # noqa: BLE001
            failure = classify_failure(exc, block_id=section_order.section.id)
            action = recovery_for(failure, ledger, sibling_block_ids=sorted(ready))
            log.warning(
                "component_lectio_block_failure generation_id=%s section=%s class=%s action=%s",
                generation_id,
                section_order.section.id,
                failure.failure_class.value,
                action.action,
            )
            if action.action in {"retry", "repair"}:
                try:
                    generated = await execute(
                        section_order,
                        emit,
                        trace_id=generation_id,
                        generation_id=generation_id,
                    )
                    for order, payload in _blocks_from_executor(
                        generated,
                        orders_by_component=orders_by_component,
                    ):
                        await _persist_ready_block(
                            generation_id,
                            block_id=order.block_id,
                            payload=payload,
                            plan_revision=canonical.plan_revision,
                            plan_hash=canonical.plan_hash,
                        )
                        ready.add(order.block_id)
                    continue
                except Exception as retry_exc:  # noqa: BLE001
                    exc = retry_exc
            for component in section_order.section.components:
                order = orders_by_component.get(component.component_id)
                if order is None or order.block_id in ready:
                    continue
                await insert_step(
                    generation_id,
                    part_id=order.block_id,
                    step=FAILED_STEP,
                    payload={
                        "error": {
                            "message": str(exc)[:400],
                            "class": failure.failure_class.value,
                        }
                    },
                )
            await persist_chunked_state(
                generation_id,
                {
                    "stage": "assembly_blocked",
                    "error": str(exc)[:400],
                    "error_type": type(exc).__name__,
                },
            )
            raise

    store = await reconstruct_checkpoint_store(
        generation_id,
        plan_revision=canonical.plan_revision,
        plan_hash=canonical.plan_hash,
        desired_work=desired,
    )
    store.mark_terminal("complete")
    document = assemble_lesson_document(
        canonical,
        store,
        title=title or (form.topic if form else "Lesson"),
    )
    from core.database.models import GenerationModel
    from core.database.session import async_session_factory

    async with async_session_factory() as session:
        model = await session.get(GenerationModel, generation_id)
        if model is not None:
            model.document_json = {
                **document,
                "status": "complete",
                "pipeline": "component_lectio",
            }
            await session.commit()

    await persist_chunked_state(
        generation_id,
        {
            "stage": "complete",
            "execution_started": True,
            "lesson_document": document,
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
    )
    return filled
