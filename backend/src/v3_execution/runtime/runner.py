from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from v3_blueprint.models import ProductionBlueprint
from v3_execution.assembly.pack_builder import V3PackBuilder
from v3_execution.assembly.section_builder import V3SectionBuilder
from v3_execution.compile_orders import compile_execution_bundle
from v3_execution.config import make_semaphores
from v3_execution.config.timeouts import V3_TIMEOUTS
from v3_execution.executors.answer_key_generator import execute_answer_key
from v3_execution.executors.question_writer import execute_questions
from v3_execution.executors.section_writer import execute_section
from v3_execution.executors.visual_executor import execute_visual
from v3_execution.models import (
    CompiledWorkOrders,
    ExecutionResult,
    GeneratedComponentBlock,
    GeneratedQuestionBlock,
    GeneratedVisualBlock,
)
from pipeline.contracts import _load_component_registry

from v3_execution.runtime import events
from v3_review import coherence_report_to_generation_summary, route_repairs, run_coherence_review


async def run_generation(
    *,
    blueprint: ProductionBlueprint,
    generation_id: str,
    blueprint_id: str,
    template_id: str,
    emit_event: Callable[[str, dict[str, Any]], Awaitable[None]],
    trace_id: str | None = None,
    model_overrides: dict | None = None,
) -> ExecutionResult:
    async def _inner() -> ExecutionResult:
        bundle = compile_execution_bundle(
            blueprint,
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            template_id=template_id,
        )
        await emit_event(
            events.WORK_ORDERS_COMPILED,
            {"generation_id": generation_id, "blueprint_id": blueprint_id},
        )

        result = ExecutionResult(
            generation_id=generation_id,
            blueprint_id=blueprint_id,
        )
        sem = make_semaphores()

        async def _guard(label: str, coro: Awaitable[list[Any]]) -> list[Any]:
            try:
                return await coro
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"{label}: {exc}")
                return []

        async def _timed_section(order: Any) -> list[Any]:
            async with sem["section_writer"]:
                return await asyncio.wait_for(
                    execute_section(
                        order,
                        emit_event,
                        trace_id=trace_id,
                        generation_id=generation_id,
                        model_overrides=model_overrides,
                    ),
                    timeout=V3_TIMEOUTS["section_writer"],
                )

        async def _timed_questions(order: Any) -> list[Any]:
            async with sem["question_writer"]:
                return await asyncio.wait_for(
                    execute_questions(
                        order,
                        emit_event,
                        trace_id=trace_id,
                        generation_id=generation_id,
                        model_overrides=model_overrides,
                    ),
                    timeout=V3_TIMEOUTS["question_writer"],
                )

        def _visual_deadline(order: Any) -> int:
            if order.visual.mode == "diagram_series" and order.visual.frames:
                return V3_TIMEOUTS["visual_executor_frame"] * max(1, len(order.visual.frames))
            return V3_TIMEOUTS["visual_executor_frame"]

        async def _timed_visual(order: Any) -> list[Any]:
            async with sem["visual_executor"]:
                return await asyncio.wait_for(
                    execute_visual(
                        order,
                        emit_event,
                        trace_id=trace_id,
                        generation_id=generation_id,
                    ),
                    timeout=_visual_deadline(order),
                )

        blueprint_only_visuals = [v for v in bundle.visual_orders if v.dependency == "blueprint_only"]
        section_tasks = [
            _guard(f"section:{order.section.id}", _timed_section(order))
            for order in bundle.section_orders
        ]
        question_tasks = [
            _guard(f"questions:{order.section_id}", _timed_questions(order))
            for order in bundle.question_orders
        ]
        visual_tasks_wave1 = [
            _guard(f"visual:{order.visual.id}", _timed_visual(order)) for order in blueprint_only_visuals
        ]

        wave1 = await asyncio.gather(*(section_tasks + question_tasks + visual_tasks_wave1))
        for batch in wave1:
            if not isinstance(batch, list):
                continue
            for item in batch:
                if isinstance(item, GeneratedComponentBlock):
                    result.component_blocks.append(item)
                elif isinstance(item, GeneratedQuestionBlock):
                    result.question_blocks.append(item)
                elif isinstance(item, GeneratedVisualBlock):
                    result.visual_blocks.append(item)

        text_visuals = [v for v in bundle.visual_orders if v.dependency != "blueprint_only"]
        if text_visuals:
            wave2 = await asyncio.gather(
                *[
                    _guard(f"visual:{order.visual.id}:late", _timed_visual(order))
                    for order in text_visuals
                ]
            )
            for batch in wave2:
                if not isinstance(batch, list):
                    continue
                for item in batch:
                    if isinstance(item, GeneratedVisualBlock):
                        result.visual_blocks.append(item)

        try:

            async def _answer_key():
                async with sem["answer_key_generator"]:
                    return await asyncio.wait_for(
                        execute_answer_key(
                            bundle.answer_key_order,
                            emit_event,
                            trace_id=trace_id,
                            generation_id=generation_id,
                            model_overrides=model_overrides,
                        ),
                        timeout=V3_TIMEOUTS["answer_key_generator"],
                    )

            result.answer_key = await _answer_key()
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"answer_key: {exc}")

        await emit_event(events.ASSEMBLY_STARTED, {"generation_id": generation_id})
        assembler = V3SectionBuilder()

        assembly_failed = False
        assembly_error = ""

        def _build_sections():
            return assembler.build_sections(
                blueprint,
                result.component_blocks,
                result.question_blocks,
                result.visual_blocks,
                template_id=template_id,
                answer_key=result.answer_key,
            )

        try:
            sections, asm_warnings = await asyncio.wait_for(
                asyncio.to_thread(_build_sections),
                timeout=V3_TIMEOUTS["assembly"],
            )
            result.warnings.extend(asm_warnings)
        except RuntimeError as exc:
            assembly_failed = True
            assembly_error = str(exc)
            sections = []
            result.warnings.append(assembly_error)
        except asyncio.TimeoutError:
            assembly_failed = True
            assembly_error = f"assembly timeout ({V3_TIMEOUTS['assembly']}s)"
            sections = []
            result.warnings.append(assembly_error)

        pack_builder = V3PackBuilder()
        draft_pack = pack_builder.build(
            blueprint=blueprint,
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            template_id=template_id,
            sections=sections,
            answer_key=result.answer_key,
            warnings=list(result.warnings),
            failed_reason=assembly_error if assembly_failed else None,
        )

        await emit_event(
            events.DRAFT_PACK_READY,
            {
                "generation_id": generation_id,
                "section_count": len(sections),
                "draft_preview": draft_pack.to_json_preview(),
            },
        )

        coherence_report_payload: dict | None = None
        try:
            async with sem["llm_coherence_reviewer"]:

                async def _coherence():
                    manifest = _load_component_registry()
                    coherence_report = await run_coherence_review(
                        blueprint,
                        draft_pack,
                        manifest,
                        emit_event,
                        trace_id=trace_id or generation_id,
                        generation_id=generation_id,
                        model_overrides=model_overrides,
                    )
                    return await route_repairs(
                        coherence_report,
                        blueprint,
                        bundle,
                        draft_pack,
                        manifest,
                        emit_event,
                        execution_result=result,
                        trace_id=trace_id or generation_id,
                        generation_id=generation_id,
                        model_overrides=model_overrides,
                    )

                draft_pack, coherence_report = await asyncio.wait_for(
                    _coherence(),
                    timeout=V3_TIMEOUTS["coherence_pipeline"],
                )
                coherence_report_payload = coherence_report_to_generation_summary(coherence_report)
        except Exception as exc:  # noqa: BLE001
            result.warnings.append(f"coherence_review: {exc}")

        await emit_event(
            events.GENERATION_COMPLETE,
            {
                "generation_id": generation_id,
                "warnings": result.warnings,
                **({"coherence_review": coherence_report_payload} if coherence_report_payload else {}),
            },
        )
        return result

    try:
        return await asyncio.wait_for(_inner(), timeout=V3_TIMEOUTS["generation_total"])
    except asyncio.TimeoutError:
        return ExecutionResult(
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            warnings=[
                f"generation_total: exceeded {V3_TIMEOUTS['generation_total']}s cap",
            ],
        )


async def sse_event_stream(
    *,
    blueprint: ProductionBlueprint,
    generation_id: str,
    blueprint_id: str,
    template_id: str,
    trace_id: str | None = None,
    model_overrides: dict | None = None,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def emit(event_type: str, payload: dict[str, Any]) -> None:
        body = dict(payload)
        body["type"] = event_type
        await queue.put(events.format_sse_payload(event_type, body))

    async def worker() -> None:
        try:
            await emit(events.GENERATION_STARTED, {"generation_id": generation_id})
            await run_generation(
                blueprint=blueprint,
                generation_id=generation_id,
                blueprint_id=blueprint_id,
                template_id=template_id,
                emit_event=emit,
                trace_id=trace_id or generation_id,
                model_overrides=model_overrides,
            )
        except Exception as exc:  # noqa: BLE001
            await emit(
                events.GENERATION_WARNING,
                {"generation_id": generation_id, "message": str(exc)},
            )
        finally:
            await queue.put(None)

    task = asyncio.create_task(worker())

    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk
    finally:
        await task


def execution_bundle_summary(bundle: CompiledWorkOrders) -> dict[str, Any]:
    return bundle.model_dump(mode="json")


__all__ = ["execution_bundle_summary", "run_generation", "sse_event_stream"]
