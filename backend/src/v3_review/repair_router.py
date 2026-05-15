from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from v3_blueprint.models import ProductionBlueprint
from v3_execution.assembly.pack_builder import V3PackBuilder
from v3_execution.assembly.section_builder import V3SectionBuilder
from v3_execution.executors.answer_key_generator import execute_answer_key
from v3_execution.executors.question_writer import execute_questions
from v3_execution.executors.section_writer import execute_section
from v3_execution.executors.visual_executor import execute_visual
from v3_execution.models import CompiledWorkOrders, DraftPack, ExecutionResult
from v3_execution.runtime import events as v3_events
from v3_execution.runtime.progress import emit_progress, titled_label

from v3_review.deterministic_checks import (
    check_expected_answers_preserved,
    check_planned_components_exist,
    check_planned_questions_exist,
    check_planned_sections_exist,
    check_planned_visuals_exist,
    run_rechecks_for_target,
)
from v3_review.models import CoherenceReport, RepairOutcome, RepairTarget, ReviewIssue, refresh_issue_counts

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


def _rebuild_draft_pack(
    blueprint: ProductionBlueprint,
    execution_result: ExecutionResult,
    draft_pack: DraftPack,
) -> DraftPack:
    assembler = V3SectionBuilder()
    sections, asm_warnings, section_diagnostics = assembler.build_sections(
        blueprint,
        execution_result.component_blocks,
        execution_result.question_blocks,
        execution_result.visual_blocks,
        template_id=draft_pack.template_id,
        answer_key=execution_result.answer_key,
    )
    warnings = list(execution_result.warnings)
    warnings.extend(asm_warnings)

    pack_builder = V3PackBuilder()
    return pack_builder.build(
        blueprint=blueprint,
        generation_id=draft_pack.generation_id,
        blueprint_id=draft_pack.blueprint_id,
        template_id=draft_pack.template_id,
        sections=sections,
        answer_key=execution_result.answer_key,
        warnings=warnings,
        booklet_status="draft_ready",
        section_diagnostics=section_diagnostics,
        booklet_issues=draft_pack.booklet_issues,
    )


def _merge_outcome_into_execution(
    execution_result: ExecutionResult,
    target: RepairTarget,
    outcome: RepairOutcome,
) -> None:
    if outcome.component_blocks:
        sid = target.section_id or outcome.component_blocks[0].section_id
        execution_result.component_blocks = [
            b for b in execution_result.component_blocks if b.section_id != sid
        ]
        execution_result.component_blocks.extend(outcome.component_blocks)
    if outcome.question_blocks:
        sid = target.section_id or outcome.question_blocks[0].section_id
        execution_result.question_blocks = [
            b for b in execution_result.question_blocks if b.section_id != sid
        ]
        execution_result.question_blocks.extend(outcome.question_blocks)
    if outcome.visual_blocks:
        attach_ref = outcome.visual_blocks[0].attaches_to
        execution_result.visual_blocks = [
            v for v in execution_result.visual_blocks if v.attaches_to != attach_ref
        ]
        execution_result.visual_blocks.extend(outcome.visual_blocks)
    if outcome.answer_key_block is not None:
        execution_result.answer_key = outcome.answer_key_block  # type: ignore[assignment]


def _filter_section_order(
    bundle: CompiledWorkOrders,
    target: RepairTarget,
):
    order = next(
        (o for o in bundle.section_orders if o.section.id == target.section_id),
        None,
    )
    if order is None:
        return None
    if target.component_id:
        comps = [c for c in order.section.components if c.component_id == target.component_id]
        if not comps:
            return None
        new_section = order.section.model_copy(update={"components": comps})
        return order.model_copy(update={"section": new_section})
    return order


def _filter_question_order(
    bundle: CompiledWorkOrders,
    target: RepairTarget,
):
    order = next(
        (o for o in bundle.question_orders if o.section_id == target.section_id),
        None,
    )
    if order is None:
        return None
    if target.question_id:
        qs = [q for q in order.questions if q.id == target.question_id]
        if not qs:
            return None
        return order.model_copy(update={"questions": qs})
    return order


def _find_visual_order(bundle: CompiledWorkOrders, target: RepairTarget):
    if target.visual_id:
        hit = next((o for o in bundle.visual_orders if o.visual.id == target.visual_id), None)
        if hit is not None:
            return hit
    if target.section_id:
        return next(
            (o for o in bundle.visual_orders if o.visual.attaches_to == target.section_id),
            None,
        )
    return None


async def dispatch_repair(
    target: RepairTarget,
    work_orders: CompiledWorkOrders,
    *,
    attempt: int,
    emit_event: EmitFn,
    trace_id: str | None,
    generation_id: str | None,
    model_overrides: dict | None,
) -> RepairOutcome:
    gid = generation_id or ""
    try:
        if target.executor == "assembler":
            return RepairOutcome(target_id=target.target_id, ok=True, attempt=attempt, errors=[])

        if target.executor == "section_writer":
            order = _filter_section_order(work_orders, target)
            if order is None:
                return RepairOutcome(
                    target_id=target.target_id,
                    ok=False,
                    attempt=attempt,
                    errors=["No matching section work order for repair target."],
                )
            blocks = await execute_section(
                order,
                emit_event,
                trace_id=trace_id,
                generation_id=gid,
                model_overrides=model_overrides,
            )
            return RepairOutcome(
                target_id=target.target_id,
                ok=True,
                attempt=attempt,
                component_blocks=list(blocks),
                errors=[],
            )

        if target.executor == "question_writer":
            order = _filter_question_order(work_orders, target)
            if order is None:
                return RepairOutcome(
                    target_id=target.target_id,
                    ok=False,
                    attempt=attempt,
                    errors=["No matching question work order for repair target."],
                )
            blocks = await execute_questions(
                order,
                emit_event,
                trace_id=trace_id,
                generation_id=gid,
                model_overrides=model_overrides,
            )
            return RepairOutcome(
                target_id=target.target_id,
                ok=True,
                attempt=attempt,
                question_blocks=list(blocks),
                errors=[],
            )

        if target.executor == "visual_executor":
            order = _find_visual_order(work_orders, target)
            if order is None:
                return RepairOutcome(
                    target_id=target.target_id,
                    ok=False,
                    attempt=attempt,
                    errors=["No matching visual work order for repair target."],
                )
            blocks = await execute_visual(
                order,
                emit_event,
                trace_id=trace_id,
                generation_id=gid,
            )
            return RepairOutcome(
                target_id=target.target_id,
                ok=True,
                attempt=attempt,
                visual_blocks=list(blocks),
                errors=[],
            )

        if target.executor == "answer_key_generator":
            if work_orders.answer_key_order is None:
                return RepairOutcome(
                    target_id=target.target_id,
                    ok=False,
                    attempt=attempt,
                    errors=["No answer key work order available."],
                )
            block = await execute_answer_key(
                work_orders.answer_key_order,
                emit_event,
                trace_id=trace_id,
                generation_id=gid,
                model_overrides=model_overrides,
            )
            return RepairOutcome(
                target_id=target.target_id,
                ok=True,
                attempt=attempt,
                answer_key_block=block,
                errors=[],
            )

    except (RuntimeError, ValueError, TypeError) as exc:
        return RepairOutcome(
            target_id=target.target_id,
            ok=False,
            attempt=attempt,
            errors=[str(exc)],
        )

    return RepairOutcome(
        target_id=target.target_id,
        ok=False,
        attempt=attempt,
        errors=["Unknown executor path."],
    )


async def route_repairs(
    report: CoherenceReport,
    blueprint: ProductionBlueprint,
    work_orders: CompiledWorkOrders,
    draft_pack: DraftPack,
    emit_event: EmitFn,
    execution_result: ExecutionResult,
    *,
    trace_id: str | None = None,
    generation_id: str | None = None,
    model_overrides: dict | None = None,
    section_titles: dict[str, str] | None = None,
) -> tuple[DraftPack, CoherenceReport]:
    gid = generation_id or draft_pack.generation_id
    titles = section_titles or {}

    targets_to_repair = [t for t in report.repair_targets if t.severity in ("blocking", "major")]

    current_pack = draft_pack

    for target in targets_to_repair:
        repair_section_id = target.section_id
        repair_title = titles.get(repair_section_id or "", None) if repair_section_id else None
        if gid:
            await emit_progress(
                emit_event,
                generation_id=gid,
                stage="repairing_section",
                label=titled_label(
                    "Repairing",
                    repair_title,
                    fallback="Repairing section",
                ),
                section_id=repair_section_id,
            )
        await emit_event(
            v3_events.REPAIR_STARTED,
            {
                "generation_id": gid,
                "target_id": target.target_id,
                "executor": target.executor,
                "reason": target.reason,
            },
        )

        repaired_cleanly = False
        for attempt_n in (1, 2):
            outcome = await dispatch_repair(
                target,
                work_orders,
                attempt=attempt_n,
                emit_event=emit_event,
                trace_id=trace_id or gid,
                generation_id=gid,
                model_overrides=model_overrides,
            )
            report.repair_attempts[target.target_id] = attempt_n

            if not outcome.ok:
                await emit_event(
                    v3_events.REPAIR_FAILED,
                    {"generation_id": gid, "target_id": target.target_id, "errors": outcome.errors},
                )
                break

            _merge_outcome_into_execution(execution_result, target, outcome)
            current_pack = _rebuild_draft_pack(blueprint, execution_result, current_pack)

            recheck_issues = run_rechecks_for_target(
                target.target_type,
                blueprint,
                current_pack,
            )
            if not any(i.severity == "blocking" for i in recheck_issues):
                report.repaired_target_ids.append(target.target_id)
                patch_payload: dict[str, object] = {
                    "generation_id": gid,
                    "target_ref": target.target_ref,
                    "target_type": target.target_type,
                    "target_id": target.target_id,
                }
                if outcome.component_blocks:
                    blk = outcome.component_blocks[0]
                    patch_payload.update(
                        {
                            "section_id": blk.section_id,
                            "component_id": blk.component_id,
                            "section_field": blk.section_field,
                            "data": blk.data,
                        }
                    )
                await emit_event(v3_events.COMPONENT_PATCHED, patch_payload)
                repaired_cleanly = True
                break
        else:
            if not repaired_cleanly:
                await emit_event(
                    v3_events.REPAIR_ESCALATED,
                    {
                        "generation_id": gid,
                        "target_id": target.target_id,
                        "reason": "Two attempts failed structural recheck",
                    },
                )

    final_issues: list[ReviewIssue] = []
    final_issues.extend(check_planned_sections_exist(blueprint, current_pack))
    final_issues.extend(check_planned_components_exist(blueprint, current_pack))
    final_issues.extend(check_planned_questions_exist(blueprint, current_pack))
    final_issues.extend(check_planned_visuals_exist(blueprint, current_pack))
    final_issues.extend(check_expected_answers_preserved(blueprint, current_pack))

    repaired_set = set(report.repaired_target_ids)
    remaining_blocking = [
        i
        for i in final_issues
        if i.severity == "blocking"
        and (i.repair_target_id is None or i.repair_target_id not in repaired_set)
    ]

    structural_blocking = sum(1 for i in final_issues if i.severity == "blocking")

    if remaining_blocking:
        report.status = "escalated"
        await emit_event(
            v3_events.REPAIR_ESCALATED,
            {
                "generation_id": gid,
                "reason": "Blocking issues remain after repairs",
            },
        )
    elif structural_blocking:
        report.status = "passed_with_warnings"
    else:
        report.status = "passed"

    report.issues = final_issues
    refresh_issue_counts(report)

    return current_pack, report


__all__ = ["dispatch_repair", "route_repairs"]
