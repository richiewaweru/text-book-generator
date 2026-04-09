"""
pipeline.graph

The LangGraph generation graph. Curriculum planner fans out into
per-section mini-pipelines:
    prepare_section -> generate_section_assets? -> finalize_section

After finalize/retry nodes, route_after_qc decides whether to rerender or finish.
"""

from __future__ import annotations

import inspect
from time import perf_counter
from typing import Any, Callable

from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from pipeline.events import (
    NodeFinishedEvent,
    NodeStartedEvent,
)
from pipeline.nodes.curriculum_planner import curriculum_planner
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.field_regenerator import field_regenerator
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.process_section import (
    finalize_section,
    generate_section_assets,
    prepare_section,
)
from pipeline.nodes.qc_agent import qc_agent
from pipeline.nodes.section_assembler import section_assembler
from pipeline.nodes.section_runner import run_section_steps
from pipeline.routers.qc_router import route_after_qc
from pipeline.runtime_context import get_runtime_context
from pipeline.runtime_diagnostics import (
    generation_id_from_state,
    next_node_attempt,
    node_error_messages,
    publish_runtime_event,
)
from pipeline.state import TextbookPipelineState


def _normalize_langgraph_config_signature(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Force the config annotation to resolve to the runtime type LangGraph expects."""
    signature = inspect.signature(fn)
    config = signature.parameters.get("config")
    expected = RunnableConfig | None

    if config is None or config.annotation == expected:
        return fn

    fn.__signature__ = signature.replace(
        parameters=[
            parameter.replace(annotation=expected)
            if parameter.name == "config"
            else parameter
            for parameter in signature.parameters.values()
        ]
    )
    return fn


async def _invoke_node(
    fn,
    state,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
):
    kwargs = {"model_overrides": model_overrides}
    if config is not None and "config" in inspect.signature(fn).parameters:
        kwargs["config"] = config
    return await fn(state, **kwargs)


def fan_out_sections(state: TextbookPipelineState | dict) -> list[Send]:
    """Fan out one per-section flow after curriculum_planner."""
    state = TextbookPipelineState.parse(state)
    if not state.curriculum_outline:
        return []

    base = state.model_dump()
    return [
        Send("prepare_section", {
            **base,
            "current_section_id": plan.section_id,
            "current_section_plan": plan.model_dump(),
        })
        for plan in state.curriculum_outline
    ]


async def _run_generation_node(
    name: str,
    fn,
    state,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
):
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
        result = await _invoke_node(
            fn,
            state,
            model_overrides=model_overrides,
            config=config,
        )
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
    config: RunnableConfig | None = None,
):
    return await _run_generation_node(
        "curriculum_planner",
        curriculum_planner,
        state,
        model_overrides=model_overrides,
        config=config,
    )


async def retry_diagram(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """
    Re-run diagram_generator -> section_assembler -> qc_agent only.

    Text content in generated_sections[sid] is preserved exactly.
    Called when QC flags only diagram blocks as blocking.
    """
    typed = TextbookPipelineState.parse(state)
    sid = typed.current_section_id
    prior_outcome = typed.diagram_outcomes.get(sid) if sid else None
    prior_retry_count = typed.diagram_retry_count.get(sid, 0) if sid else 0
    runtime_context = get_runtime_context(config)

    if runtime_context is not None and sid is not None:
        await runtime_context.progress.start_retry(sid)

    try:
        if prior_outcome == "timeout" or prior_retry_count >= 1:
            return await run_section_steps(
                typed,
                steps=[
                    ("section_assembler", section_assembler),
                    ("qc_agent", qc_agent),
                ],
                model_overrides=model_overrides,
                increment_rerender_count=True,
                config=config,
            )

        raw_state = typed.model_dump()
        if sid:
            raw_state["diagram_retry_count"] = {
                **typed.diagram_retry_count,
                sid: prior_retry_count + 1,
            }

        return await run_section_steps(
            raw_state,
            steps=[
                ("diagram_generator", diagram_generator),
                ("section_assembler", section_assembler),
                ("qc_agent", qc_agent),
            ],
            model_overrides=model_overrides,
            increment_rerender_count=True,
            config=config,
        )
    finally:
        if runtime_context is not None and sid is not None:
            await runtime_context.progress.finish_retry(sid)


async def retry_field(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Re-run field_regenerator -> section_assembler -> qc_agent only."""
    typed = TextbookPipelineState.parse(state)
    runtime_context = get_runtime_context(config)
    sid = typed.current_section_id
    if runtime_context is not None and sid is not None:
        await runtime_context.progress.start_retry(sid)
    try:
        return await run_section_steps(
            state,
            steps=[
                ("field_regenerator", field_regenerator),
                ("section_assembler", section_assembler),
                ("qc_agent", qc_agent),
            ],
            model_overrides=model_overrides,
            increment_rerender_count=True,
            config=config,
        )
    finally:
        if runtime_context is not None and sid is not None:
            await runtime_context.progress.finish_retry(sid)


async def retry_interaction(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """
    Re-run interaction_generator -> section_assembler -> qc_agent only.

    Text content and diagram in generated_sections[sid] are preserved exactly.
    Called when QC flags only simulation/interaction blocks as blocking.
    Does NOT consume max_rerenders budget.
    """
    typed = TextbookPipelineState.parse(state)
    sid = typed.current_section_id
    prior_retry_count = typed.interaction_retry_count.get(sid, 0) if sid else 0
    runtime_context = get_runtime_context(config)

    if runtime_context is not None and sid is not None:
        await runtime_context.progress.start_retry(sid)

    try:
        raw_state = typed.model_dump()
        if sid:
            raw_state["interaction_retry_count"] = {
                **typed.interaction_retry_count,
                sid: prior_retry_count + 1,
            }

        return await run_section_steps(
            raw_state,
            steps=[
                ("interaction_generator", interaction_generator),
                ("section_assembler", section_assembler),
                ("qc_agent", qc_agent),
            ],
            model_overrides=model_overrides,
            increment_rerender_count=False,  # does NOT consume max_rerenders
            config=config,
        )
    finally:
        if runtime_context is not None and sid is not None:
            await runtime_context.progress.finish_retry(sid)


def route_after_prepare_section(state: TextbookPipelineState | dict) -> str:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is None:
        return END
    if section_id in typed.failed_sections:
        return END
    if section_id not in typed.generated_sections:
        return END
    if typed.section_pending_assets.get(section_id):
        return "generate_section_assets"
    return "finalize_section"


def route_after_generate_section_assets(state: TextbookPipelineState | dict) -> str:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    if section_id is None:
        return END
    if section_id in typed.failed_sections:
        return END
    if section_id not in typed.generated_sections:
        return END
    return "finalize_section"


def build_graph(checkpointer=None) -> StateGraph:
    workflow = StateGraph(TextbookPipelineState)

    # Register nodes
    workflow.add_node(
        "curriculum_planner",
        _normalize_langgraph_config_signature(_instrumented_curriculum_planner),
    )
    workflow.add_node(
        "prepare_section",
        _normalize_langgraph_config_signature(prepare_section),
    )
    workflow.add_node(
        "generate_section_assets",
        _normalize_langgraph_config_signature(generate_section_assets),
    )
    workflow.add_node(
        "finalize_section",
        _normalize_langgraph_config_signature(finalize_section),
    )
    workflow.add_node(
        "retry_diagram",
        _normalize_langgraph_config_signature(retry_diagram),
    )
    workflow.add_node("retry_field", _normalize_langgraph_config_signature(retry_field))
    workflow.add_node(
        "retry_interaction",
        _normalize_langgraph_config_signature(retry_interaction),
    )

    # Entry point
    workflow.set_entry_point("curriculum_planner")

    # After curriculum_planner: fan out per section
    workflow.add_conditional_edges(
        "curriculum_planner",
        fan_out_sections,
    )

    workflow.add_conditional_edges("prepare_section", route_after_prepare_section)
    workflow.add_conditional_edges(
        "generate_section_assets",
        route_after_generate_section_assets,
    )
    workflow.add_conditional_edges("finalize_section", route_after_qc)

    # Diagram-only retry: re-run diagram + assembler + QC, then re-evaluate.
    workflow.add_conditional_edges("retry_diagram", route_after_qc)

    # Field-level retry: regenerate one text field, then re-evaluate.
    workflow.add_conditional_edges("retry_field", route_after_qc)

    # Interaction-only retry: re-run interaction_generator + assembler + QC.
    workflow.add_conditional_edges("retry_interaction", route_after_qc)

    return workflow.compile(checkpointer=checkpointer or MemorySaver())
