"""
diagram_generator node -- generates structured diagram specs.

Reads:
    current_section_id, generated_sections, style_context, contract, composition_plans
Writes:
    generated_sections[current_section_id].diagram, diagram_outcomes, completed_nodes, errors
"""

from __future__ import annotations

import asyncio

from core.config import settings as app_settings
from core.llm.logging import NodeLogger
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel
from pydantic_ai import Agent

from pipeline.events import DiagramOutcomeEvent
from pipeline.llm_runner import run_llm
from pipeline.prompts.diagram import (
    build_diagram_system_prompt,
    build_diagram_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_context import retry_policy_for_node, timeout_policy_from_config
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.runtime_policy import resolve_runtime_policy_bundle
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.types.section_content import DiagramContent, DiagramSpec

_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}


class DiagramOutput(BaseModel):
    spec: DiagramSpec
    caption: str
    alt_text: str


def _has_diagram_slot(contract) -> bool:
    all_components = set(contract.required_components) | set(contract.optional_components)
    return bool(_DIAGRAM_COMPONENTS & all_components)


def _get_diagram_slot(contract) -> str:
    for slot in ("diagram-block", "diagram-series", "diagram-compare"):
        if slot in contract.required_components or slot in contract.optional_components:
            return slot
    return "diagram-block"


def _publish_outcome(generation_id: str, section_id: str | None, outcome: str) -> None:
    if section_id is None:
        return
    normalized = {
        "spec_success": "success",
        "skipped_image_mode": "skipped",
    }.get(outcome, outcome)
    publish_runtime_event(
        generation_id,
        DiagramOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=normalized,
        ),
    )


async def _generate_spec_diagram(
    state: TextbookPipelineState,
    section,
    section_id: str,
    plan: object | None,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    model = get_node_text_model(
        "diagram_generator",
        model_overrides=model_overrides,
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=DiagramOutput,
        system_prompt=build_diagram_system_prompt(state.style_context),
    )
    timeout_policy = timeout_policy_from_config(config)
    retry_policy = retry_policy_for_node(config, "diagram_generator")
    if timeout_policy is None or retry_policy is None:
        policy = resolve_runtime_policy_bundle(app_settings, state.request.mode)
        timeout_policy = timeout_policy or policy.timeouts
        retry_policy = retry_policy or policy.retries.for_node("diagram_generator")

    result = await asyncio.wait_for(
        run_llm(
            generation_id=state.request.generation_id or "",
            node="diagram_generator",
            agent=agent,
            model=model,
            user_prompt=build_diagram_user_prompt(
                section_title=section.header.title,
                hook_body=section.hook.body,
                explanation_excerpt=section.explanation.body,
                diagram_slot=_get_diagram_slot(state.contract),
                diagram_type=plan.diagram.diagram_type if plan is not None else None,
                key_concepts=plan.diagram.key_concepts if plan is not None else None,
                visual_guidance=plan.diagram.visual_guidance if plan is not None else None,
            ),
            generation_mode=state.request.mode,
            retry_policy=retry_policy,
        ),
        timeout=timeout_policy.diagram_node_budget_seconds,
    )

    diagram = DiagramContent(
        spec=result.output.spec,
        caption=result.output.caption,
        alt_text=result.output.alt_text,
    )
    updated = section.model_copy(update={"diagram": diagram})
    return {"generated_sections": {section_id: updated}}


async def diagram_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    _ = NodeLogger(
        generation_id=state.request.generation_id or "",
        section_id=sid,
        node_name="diagram_generator",
    )
    outcomes = dict(state.diagram_outcomes)
    plan = state.composition_plans.get(sid)

    if not _has_diagram_slot(state.contract):
        if sid:
            outcomes[sid] = "skipped"
            _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if plan is not None and plan.diagram.mode == "image":
        if sid:
            outcomes[sid] = "skipped_image_mode"
            _publish_outcome(state.request.generation_id or "", sid, "skipped_image_mode")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if plan is not None and not plan.diagram.enabled:
        outcomes[sid] = "skipped"
        _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if plan is None and state.current_section_plan and not state.current_section_plan.needs_diagram:
        outcomes[sid] = "skipped"
        _publish_outcome(state.request.generation_id or "", sid, "skipped")
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if state.style_context is None:
        outcomes[sid] = "error"
        _publish_outcome(state.request.generation_id or "", sid, "error")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message="style_context is None -- curriculum_planner may have failed",
                    recoverable=False,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }

    try:
        spec_result = await _generate_spec_diagram(
            state,
            section,
            sid,
            plan,
            model_overrides=model_overrides,
            config=config,
        )
        outcomes[sid] = "spec_success"
        _publish_outcome(state.request.generation_id or "", sid, "spec_success")
        return {
            **spec_result,
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
    except asyncio.TimeoutError:
        timeout_policy = timeout_policy_from_config(config)
        if timeout_policy is None:
            timeout_policy = resolve_runtime_policy_bundle(app_settings, state.request.mode).timeouts
        outcomes[sid] = "timeout"
        _publish_outcome(state.request.generation_id or "", sid, "timeout")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=(
                        f"Diagram generation timed out ({int(timeout_policy.diagram_node_budget_seconds)}s) "
                        "and the section will ship without a diagram."
                    ),
                    recoverable=True,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
    except Exception as exc:
        outcomes[sid] = "error"
        _publish_outcome(state.request.generation_id or "", sid, "error")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=f"Diagram generation failed: {exc}",
                    recoverable=True,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
