"""
diagram_generator node -- real implementation.

STATE CONTRACT
    Reads:  current_section_id, current_section_plan, generated_sections,
            style_context, contract
    Writes: generated_sections[current_section_id].diagram, completed_nodes, errors
    Slot:   FAST
    Skips:  if no diagram slot in contract OR section plan says needs_diagram=False
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent

from pipeline.prompts.diagram import (
    build_diagram_system_prompt,
    build_diagram_user_prompt,
)
from pipeline.providers.registry import get_node_text_model
from pipeline.state import PipelineError, TextbookPipelineState
from pipeline.types.section_content import DiagramContent
from pipeline.llm_runner import run_llm

_DIAGRAM_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare"}


class DiagramOutput(BaseModel):
    svg_content: str
    caption: str
    alt_text: str


def _has_diagram_slot(contract) -> bool:
    """Return whether the active contract can accept any diagram component."""

    all_components = set(contract.required_components) | set(
        contract.optional_components
    )
    return bool(_DIAGRAM_COMPONENTS & all_components)


def _get_diagram_slot(contract) -> str:
    """Pick the first compatible diagram slot expected by the template."""

    for slot in ("diagram-block", "diagram-series", "diagram-compare"):
        if (
            slot in contract.required_components
            or slot in contract.optional_components
        ):
            return slot
    return "diagram-block"


async def diagram_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Generate the optional visual explanation for the current section."""

    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id

    # Skip if template has no diagram component
    if not _has_diagram_slot(state.contract):
        return {"completed_nodes": ["diagram_generator"]}

    section = state.generated_sections.get(sid)
    if section is None:
        return {"completed_nodes": ["diagram_generator"]}

    # Skip if curriculum_planner flagged this section as not needing a diagram
    plan = state.current_section_plan
    if plan and not plan.needs_diagram:
        return {"completed_nodes": ["diagram_generator"]}

    if state.style_context is None:
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message="style_context is None -- curriculum_planner may have failed",
                    recoverable=False,
                )
            ],
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
                ),
                generation_mode=state.request.mode,
            ),
            timeout=25.0,
        )

        diagram = DiagramContent(
            svg_content=result.output.svg_content,
            caption=result.output.caption,
            alt_text=result.output.alt_text,
        )

        updated = section.model_copy(update={"diagram": diagram})
        generated = dict(state.generated_sections)
        generated[sid] = updated

        return {
            "generated_sections": generated,
            "completed_nodes": ["diagram_generator"],
        }

    except asyncio.TimeoutError:
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message="Diagram generation timed out (25s) — section delivered without diagram",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["diagram_generator"],
        }

    except Exception as e:
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message=f"Diagram generation failed: {e}",
                    recoverable=True,
                )
            ],
            "completed_nodes": ["diagram_generator"],
        }
