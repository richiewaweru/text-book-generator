"""
pipeline.graph

The LangGraph generation graph. Curriculum planner fans out into
per-section mini-pipelines (process_section), then QC runs over everything.
"""

from __future__ import annotations

from time import perf_counter

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Send

from pipeline.api import PipelineSectionReport
from pipeline.events import (
    NodeFinishedEvent,
    NodeStartedEvent,
    SectionReportUpdatedEvent,
    SectionRetryQueuedEvent,
)
from pipeline.nodes.curriculum_planner import curriculum_planner
from pipeline.nodes.process_section import process_section
from pipeline.nodes.qc_agent import qc_agent
from pipeline.routers.qc_router import route_after_qc
from pipeline.runtime_diagnostics import (
    generation_id_from_state,
    next_node_attempt,
    node_error_messages,
    publish_runtime_event,
)
from pipeline.state import TextbookPipelineState


def fan_out_sections(state: TextbookPipelineState | dict) -> list[Send]:
    """Fan out one composite mini-pipeline per section after curriculum_planner."""
    state = TextbookPipelineState.parse(state)
    if not state.curriculum_outline:
        return []

    base = state.model_dump()
    return [
        Send("process_section", {
            **base,
            "current_section_id": plan.section_id,
            "current_section_plan": plan.model_dump(),
        })
        for plan in state.curriculum_outline
    ]


async def _run_generation_node(name: str, fn, state, *, model_overrides: dict | None = None):
    typed = TextbookPipelineState.parse(state)
    generation_id = generation_id_from_state(typed)
    attempt = next_node_attempt(generation_id, name) if generation_id else 1
    started = perf_counter()

    publish_runtime_event(
        generation_id,
        NodeStartedEvent(
            generation_id=generation_id,
            node=name,
            attempt=attempt,
        ),
    )

    try:
        result = await fn(state, model_overrides=model_overrides)
    except Exception as exc:
        publish_runtime_event(
            generation_id,
            NodeFinishedEvent(
                generation_id=generation_id,
                node=name,
                attempt=attempt,
                status="failed",
                latency_ms=(perf_counter() - started) * 1000.0,
                error=str(exc),
            ),
        )
        raise

    messages = node_error_messages(result.get("errors"), node=name)
    publish_runtime_event(
        generation_id,
        NodeFinishedEvent(
            generation_id=generation_id,
            node=name,
            attempt=attempt,
            status="failed" if messages else "succeeded",
            latency_ms=(perf_counter() - started) * 1000.0,
            error=" | ".join(messages) if messages else None,
        ),
    )

    if name == "qc_agent":
        for section_id, report in result.get("qc_reports", {}).items():
            publish_runtime_event(
                generation_id,
                SectionReportUpdatedEvent(
                    generation_id=generation_id,
                    section_id=section_id,
                    source="qc_agent",
                    report=PipelineSectionReport.model_validate(report),
                ),
            )

        for request in result.get("rerender_requests", []):
            if isinstance(request, dict):
                section_id = request.get("section_id")
                reason = request.get("reason", "QC failed")
                block_type = request.get("block_type", "unknown")
            else:
                section_id = getattr(request, "section_id", None)
                reason = getattr(request, "reason", "QC failed")
                block_type = getattr(request, "block_type", "unknown")
            next_attempt = typed.rerender_count.get(section_id, 0) + 2 if section_id else 2
            publish_runtime_event(
                generation_id,
                SectionRetryQueuedEvent(
                    generation_id=generation_id,
                    section_id=section_id or "unknown",
                    reason=reason,
                    block_type=block_type,
                    next_attempt=next_attempt,
                    max_attempts=typed.max_rerenders + 1,
                ),
            )

    return result


async def _instrumented_curriculum_planner(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
):
    return await _run_generation_node(
        "curriculum_planner",
        curriculum_planner,
        state,
        model_overrides=model_overrides,
    )


async def _instrumented_qc_agent(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
):
    return await _run_generation_node(
        "qc_agent",
        qc_agent,
        state,
        model_overrides=model_overrides,
    )


def build_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(TextbookPipelineState)

    # Register nodes
    workflow.add_node("curriculum_planner", _instrumented_curriculum_planner)
    workflow.add_node("process_section", process_section)
    workflow.add_node("qc_agent", _instrumented_qc_agent)

    # Entry point
    workflow.set_entry_point("curriculum_planner")

    # After curriculum_planner: fan out per section
    workflow.add_conditional_edges(
        "curriculum_planner",
        fan_out_sections,
    )

    # All sections join at QC
    workflow.add_edge("process_section", "qc_agent")

    # QC routes: router returns list[Send] for rerenders or END
    workflow.add_conditional_edges("qc_agent", route_after_qc)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())
