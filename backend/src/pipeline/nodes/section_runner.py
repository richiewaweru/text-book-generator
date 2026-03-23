from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from time import perf_counter
from typing import Any

from pipeline.api import PipelineSectionReport
from pipeline.events import (
    NodeFinishedEvent,
    NodeStartedEvent,
    SectionAttemptStartedEvent,
    SectionReportUpdatedEvent,
    SectionRetryQueuedEvent,
)
from pipeline.runtime_diagnostics import (
    current_section_attempt,
    generation_id_from_state,
    node_error_messages,
    publish_runtime_event,
)
from pipeline.state import QCReport, RerenderRequest, TextbookPipelineState, merge_state_updates

SectionStep = Callable[..., Awaitable[dict]]
NamedSectionStep = tuple[str, SectionStep]

_SECTION_REPORT_SOURCES = {
    "section_assembler": "assembler",
    "qc_agent": "qc_agent",
}


def _report_source_for(node_name: str) -> str | None:
    return _SECTION_REPORT_SOURCES.get(node_name)


def _coerce_report(report: Any) -> PipelineSectionReport:
    qc_report = report if isinstance(report, QCReport) else QCReport.model_validate(report)
    return PipelineSectionReport.from_qc_report(qc_report)


def _coerce_rerender_request(request: Any) -> RerenderRequest:
    return request if isinstance(request, RerenderRequest) else RerenderRequest.model_validate(request)


def _rerender_request_changed(before: RerenderRequest | None, after: RerenderRequest | None) -> bool:
    if before is None and after is None:
        return False
    if before is None or after is None:
        return True
    return before.model_dump() != after.model_dump()


def _rerender_request_updates(
    before_state: TextbookPipelineState,
    after_state: TextbookPipelineState,
    section_id: str | None,
) -> dict[str, RerenderRequest | None]:
    if not section_id:
        return {}

    before_request = before_state.pending_rerender_for(section_id)
    after_request = after_state.pending_rerender_for(section_id)
    if not _rerender_request_changed(before_request, after_request):
        return {}
    return {section_id: after_request}


def _build_section_output(
    before_state: TextbookPipelineState,
    after_state: TextbookPipelineState,
    *,
    section_id: str | None,
    completed_nodes: Sequence[str],
) -> dict[str, Any]:
    output: dict[str, Any] = {"completed_nodes": list(completed_nodes)}

    if section_id and section_id in after_state.generated_sections:
        output["generated_sections"] = {section_id: after_state.generated_sections[section_id]}
    if section_id and section_id in after_state.assembled_sections:
        output["assembled_sections"] = {section_id: after_state.assembled_sections[section_id]}
    if section_id and section_id in after_state.interaction_specs:
        output["interaction_specs"] = {section_id: after_state.interaction_specs[section_id]}
    if section_id and section_id in after_state.qc_reports:
        output["qc_reports"] = {section_id: after_state.qc_reports[section_id]}

    rerender_updates = _rerender_request_updates(before_state, after_state, section_id)
    if rerender_updates:
        output["rerender_requests"] = rerender_updates

    if (
        section_id
        and after_state.rerender_count.get(section_id)
        != before_state.rerender_count.get(section_id)
    ):
        output["rerender_count"] = {
            section_id: after_state.rerender_count.get(section_id, 0)
        }

    new_errors = after_state.errors[len(before_state.errors) :]
    if new_errors:
        output["errors"] = new_errors

    return output


async def run_section_steps(
    state: TextbookPipelineState | dict,
    *,
    steps: Sequence[NamedSectionStep | SectionStep],
    model_overrides: dict | None = None,
    increment_rerender_count: bool = False,
) -> dict[str, Any]:
    """
    Run a section-scoped composite node and publish per-step diagnostics.

    The helper keeps section outputs isolated so concurrent fan-out branches do
    not leak unrelated sections back into LangGraph state.
    """

    before_state = TextbookPipelineState.parse(state)
    raw = before_state.model_dump()
    section_id = before_state.current_section_id
    generation_id = generation_id_from_state(before_state)
    attempt, trigger = current_section_attempt(before_state, section_id)

    if increment_rerender_count and trigger == "rerender" and section_id:
        rerender_count = dict(before_state.rerender_count)
        rerender_count[section_id] = before_state.rerender_count.get(section_id, 0) + 1
        raw["rerender_count"] = rerender_count

    if generation_id and section_id and attempt is not None:
        publish_runtime_event(
            generation_id,
            SectionAttemptStartedEvent(
                generation_id=generation_id,
                section_id=section_id,
                attempt=attempt,
                trigger=trigger,
            ),
        )

    normalized_steps: list[NamedSectionStep] = []
    for step in steps:
        if isinstance(step, tuple):
            normalized_steps.append(step)
        else:
            normalized_steps.append((step.__name__, step))

    for node_name, step in normalized_steps:
        step_started = perf_counter()

        if generation_id:
            publish_runtime_event(
                generation_id,
                NodeStartedEvent(
                    generation_id=generation_id,
                    node=node_name,
                    section_id=section_id,
                    attempt=attempt,
                ),
            )

        try:
            result = await step(raw, model_overrides=model_overrides)
        except Exception as exc:
            publish_runtime_event(
                generation_id,
                NodeFinishedEvent(
                    generation_id=generation_id,
                    node=node_name,
                    section_id=section_id,
                    attempt=attempt,
                    status="failed",
                    latency_ms=(perf_counter() - step_started) * 1000.0,
                    error=str(exc),
                ),
            )
            raise

        merge_state_updates(raw, result)
        step_state = TextbookPipelineState.parse(raw)

        step_errors = node_error_messages(
            result.get("errors"),
            node=node_name,
            section_id=section_id,
        )
        publish_runtime_event(
            generation_id,
            NodeFinishedEvent(
                generation_id=generation_id,
                node=node_name,
                section_id=section_id,
                attempt=attempt,
                status="failed" if step_errors else "succeeded",
                latency_ms=(perf_counter() - step_started) * 1000.0,
                error=" | ".join(step_errors) if step_errors else None,
            ),
        )

        source = _report_source_for(node_name)
        if (
            source is not None
            and generation_id
            and section_id
            and section_id in result.get("qc_reports", {})
        ):
            publish_runtime_event(
                generation_id,
                SectionReportUpdatedEvent(
                    generation_id=generation_id,
                    section_id=section_id,
                    source=source,
                    report=_coerce_report(result["qc_reports"][section_id]),
                ),
            )

        if node_name == "qc_agent" and generation_id:
            for rerender in result.get("rerender_requests", {}).values():
                if rerender is None:
                    continue
                request = _coerce_rerender_request(rerender)
                publish_runtime_event(
                    generation_id,
                    SectionRetryQueuedEvent(
                        generation_id=generation_id,
                        section_id=request.section_id,
                        reason=request.reason,
                        block_type=request.block_type,
                        next_attempt=step_state.rerender_count.get(request.section_id, 0) + 2,
                        max_attempts=step_state.max_rerenders + 1,
                    ),
                )

    after_state = TextbookPipelineState.parse(raw)
    return _build_section_output(
        before_state,
        after_state,
        section_id=section_id,
        completed_nodes=[node_name for node_name, _step in normalized_steps],
    )
