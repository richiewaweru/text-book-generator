"""
pipeline.run -- public entrypoint for the generation engine.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from pipeline.api import (
    PipelineCommand,
    PipelineDocument,
    PipelineErrorInfo,
    PipelineResult,
    PipelineSectionManifestItem,
    PipelineSectionReport,
)
from pipeline.contracts import get_contract
from pipeline.events import (
    PipelineEvent,
    PipelineStartEvent,
    QCCompleteEvent,
    SectionReadyEvent,
    SectionStartedEvent,
)
from pipeline.graph import build_graph
from pipeline.state import PipelineStatus, TextbookPipelineState, merge_state_updates
from pipeline.types.section_content import SectionContent
from pipeline.types.template_contract import TemplateContractSummary

__all__ = [
    "SectionContent",
    "PipelineCommand",
    "PipelineDocument",
    "PipelineResult",
    "PipelineStatus",
    "TemplateContractSummary",
    "run_pipeline",
    "run_pipeline_streaming",
    "build_graph",
]


async def _emit(
    event: PipelineEvent,
    on_event: Callable[[PipelineEvent], Awaitable[None] | None] | None,
) -> None:
    if on_event is None:
        return
    maybe_awaitable = on_event(event)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


def _merge_state(final_state: dict[str, Any], output: dict[str, Any]) -> None:
    merge_state_updates(final_state, output)


def _sorted_sections(
    state: TextbookPipelineState,
) -> list[SectionContent]:
    if not state.curriculum_outline:
        return list(state.assembled_sections.values())

    ordered: list[SectionContent] = []
    for plan in sorted(state.curriculum_outline, key=lambda item: item.position):
        section = state.assembled_sections.get(plan.section_id)
        if section is not None:
            ordered.append(section)
    return ordered


def _build_section_manifest(state: TextbookPipelineState) -> list[PipelineSectionManifestItem]:
    if not state.curriculum_outline:
        return []

    return [
        PipelineSectionManifestItem(
            section_id=plan.section_id,
            title=plan.title,
            position=plan.position,
        )
        for plan in sorted(state.curriculum_outline, key=lambda item: item.position)
    ]


def _build_reports(state: TextbookPipelineState) -> list[PipelineSectionReport]:
    reports = [
        PipelineSectionReport.from_qc_report(report)
        for report in state.qc_reports.values()
    ]
    reports.sort(key=lambda item: item.section_id)
    return reports


def _build_document(
    command: PipelineCommand,
    state: TextbookPipelineState,
    *,
    status: str,
    generation_time_seconds: float,
    error: str | None = None,
) -> PipelineDocument:
    reports = _build_reports(state)
    quality_passed = all(report.passed for report in reports) if reports else None
    completed_at = datetime.now(timezone.utc) if status in {"completed", "failed"} else None

    return PipelineDocument(
        generation_id=command.generation_id or "",
        subject=command.subject,
        context=command.context,
        mode=command.mode,
        template_id=command.template_id,
        preset_id=command.preset_id,
        source_generation_id=command.source_generation_id,
        status=status,
        section_manifest=_build_section_manifest(state),
        sections=_sorted_sections(state),
        qc_reports=reports,
        quality_passed=quality_passed,
        error=error,
        updated_at=datetime.now(timezone.utc),
        completed_at=completed_at,
    )


def _build_result(
    command: PipelineCommand,
    raw_state: dict[str, Any],
    generation_time_seconds: float,
) -> PipelineResult:
    state = TextbookPipelineState.parse(raw_state)
    document = _build_document(
        command,
        state,
        status="completed",
        generation_time_seconds=generation_time_seconds,
    )
    return PipelineResult(
        document=document,
        completed_nodes=list(state.completed_nodes),
        errors=[
            PipelineErrorInfo(
                node=error.node,
                message=error.message,
                section_id=error.section_id,
                recoverable=error.recoverable,
            )
            for error in state.errors
        ],
        generation_time_seconds=generation_time_seconds,
    )


async def run_pipeline(
    command: PipelineCommand,
) -> PipelineResult:
    return await run_pipeline_streaming(command)


async def run_pipeline_streaming(
    command: PipelineCommand,
    on_event: Callable[[PipelineEvent], Awaitable[None] | None] | None = None,
) -> PipelineResult:
    contract = get_contract(command.template_id)
    graph = build_graph()
    initial = TextbookPipelineState(
        request=command,
        contract=contract,
        max_rerenders=command.max_rerenders(),
        status=PipelineStatus.RUNNING,
    )
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    await _emit(
        PipelineStartEvent(
            generation_id=command.generation_id or "",
            section_count=command.section_count,
            template_id=command.template_id,
            preset_id=command.preset_id,
            mode=command.mode.value,
        ),
        on_event,
    )

    final_state: dict[str, Any] = initial.model_dump()
    started = perf_counter()
    emitted_started_sections = False

    async for chunk in graph.astream(initial.model_dump(), config=config):
        for node_name, output in chunk.items():
            if node_name == "__end__":
                continue

            if isinstance(output, dict):
                _merge_state(final_state, output)

            typed_state = TextbookPipelineState.parse(final_state)

            if node_name == "curriculum_planner" and not emitted_started_sections:
                for plan in typed_state.curriculum_outline or []:
                    await _emit(
                        SectionStartedEvent(
                            generation_id=command.generation_id or "",
                            section_id=plan.section_id,
                            title=plan.title,
                            position=plan.position,
                        ),
                        on_event,
                    )
                emitted_started_sections = True

            if node_name in {"process_section", "retry_diagram", "retry_field"}:
                assembled = output.get("assembled_sections", {}) if isinstance(output, dict) else {}
                total_sections = len(typed_state.curriculum_outline or []) or command.section_count
                completed_sections = len(typed_state.assembled_sections)
                for section_id, section in assembled.items():
                    await _emit(
                        SectionReadyEvent(
                            generation_id=command.generation_id or "",
                            section_id=section_id,
                            section=(
                                section
                                if isinstance(section, SectionContent)
                                else SectionContent.model_validate(section)
                            ),
                            completed_sections=completed_sections,
                            total_sections=total_sections,
                        ),
                        on_event,
                    )

                # QC is now inline in process_section.
                # Emit QCCompleteEvent when all sections have QC reports.
                reports = typed_state.qc_reports
                if reports and len(reports) >= total_sections:
                    await _emit(
                        QCCompleteEvent(
                            generation_id=command.generation_id or "",
                            passed=sum(1 for report in reports.values() if report.passed),
                            total=len(reports),
                        ),
                        on_event,
                    )

    return _build_result(command, final_state, perf_counter() - started)
