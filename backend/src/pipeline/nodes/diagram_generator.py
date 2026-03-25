"""
diagram_generator node.

Reads:
    current_section_id, generated_sections, style_context, contract, composition_plans
Writes:
    generated_sections[current_section_id].diagram, diagram_outcomes, completed_nodes, errors
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent

from pipeline.events import DiagramOutcomeEvent
from pipeline.prompts.diagram import (
    build_diagram_system_prompt,
    build_diagram_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.runtime_diagnostics import publish_runtime_event
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.types.requests import GenerationMode
from pipeline.types.section_content import DiagramContent
from pipeline.llm_runner import run_llm

_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}
_DIAGRAM_TIMEOUTS = {
    GenerationMode.DRAFT: 20.0,
    GenerationMode.BALANCED: 35.0,
    GenerationMode.STRICT: 45.0,
}


class DiagramOutput(BaseModel):
    svg_content: str
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


def _get_diagram_timeout(mode: GenerationMode) -> float:
    return _DIAGRAM_TIMEOUTS.get(mode, 25.0)


def _publish_outcome(generation_id: str, section_id: str | None, outcome: str) -> None:
    if section_id is None:
        return
    publish_runtime_event(
        generation_id,
        DiagramOutcomeEvent(
            generation_id=generation_id,
            section_id=section_id,
            outcome=outcome,
        ),
    )


async def diagram_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Generate an optional visual explanation for the current section."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    outcomes = dict(state.diagram_outcomes)
    plan = state.composition_plans.get(sid)

    if not _has_diagram_slot(state.contract):
        if sid:
            outcomes[sid] = "skipped"
            _publish_outcome(state.request.generation_id or "", sid, "skipped")
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

    try:
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
            ),
            timeout=_get_diagram_timeout(state.request.mode),
        )

        diagram = DiagramContent(
            svg_content=result.output.svg_content,
            caption=result.output.caption,
            alt_text=result.output.alt_text,
        )
        updated = section.model_copy(update={"diagram": diagram})
        generated = dict(state.generated_sections)
        generated[sid] = updated
        outcomes[sid] = "success"
        _publish_outcome(state.request.generation_id or "", sid, "success")
        return {
            "generated_sections": generated,
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }
    except asyncio.TimeoutError:
        outcomes[sid] = "timeout"
        _publish_outcome(state.request.generation_id or "", sid, "timeout")
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=(
                        f"Diagram generation timed out ({int(_get_diagram_timeout(state.request.mode))}s) "
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
