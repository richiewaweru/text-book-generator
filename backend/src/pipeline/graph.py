"""
pipeline.graph

The LangGraph generation graph. Curriculum planner fans out into
per-section mini-pipelines (process_section) which include inline QC,
then route_after_qc decides whether to rerender or finish.
"""

from __future__ import annotations

from time import perf_counter

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.types import Send

from pipeline.events import (
    NodeFinishedEvent,
    NodeStartedEvent,
)
from pipeline.nodes.curriculum_planner import curriculum_planner
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.field_regenerator import field_regenerator
from pipeline.nodes.process_section import process_section
from pipeline.nodes.qc_agent import qc_agent
from pipeline.nodes.section_assembler import section_assembler
from pipeline.nodes.section_runner import run_section_steps
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


async def retry_diagram(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """
    Re-run diagram_generator -> section_assembler -> qc_agent only.

    Text content in generated_sections[sid] is preserved exactly.
    Called when QC flags only diagram blocks as blocking.
    """
    return await run_section_steps(
        state,
        steps=[
            ("diagram_generator", diagram_generator),
            ("section_assembler", section_assembler),
            ("qc_agent", qc_agent),
        ],
        model_overrides=model_overrides,
        increment_rerender_count=True,
    )


async def retry_field(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Re-run field_regenerator -> section_assembler -> qc_agent only."""

    return await run_section_steps(
        state,
        steps=[
            ("field_regenerator", field_regenerator),
            ("section_assembler", section_assembler),
            ("qc_agent", qc_agent),
        ],
        model_overrides=model_overrides,
        increment_rerender_count=True,
    )


def build_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(TextbookPipelineState)

    # Register nodes
    workflow.add_node("curriculum_planner", _instrumented_curriculum_planner)
    workflow.add_node("process_section", process_section)
    workflow.add_node("retry_diagram", retry_diagram)
    workflow.add_node("retry_field", retry_field)

    # Entry point
    workflow.set_entry_point("curriculum_planner")

    # After curriculum_planner: fan out per section
    workflow.add_conditional_edges(
        "curriculum_planner",
        fan_out_sections,
    )

    # QC is now inline in process_section.
    # After all sections complete, route_after_qc reads qc_reports
    # and either ends or fans out rerenders to the narrowest scope.
    workflow.add_conditional_edges("process_section", route_after_qc)

    # Diagram-only retry: re-run diagram + assembler + QC, then re-evaluate.
    workflow.add_conditional_edges("retry_diagram", route_after_qc)

    # Field-level retry: regenerate one text field, then re-evaluate.
    workflow.add_conditional_edges("retry_field", route_after_qc)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())
