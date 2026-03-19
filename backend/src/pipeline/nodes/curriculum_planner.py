"""
curriculum_planner node.

STATE CONTRACT
    Reads:  request, contract
    Writes: curriculum_outline, style_context, completed_nodes, errors
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from pipeline.contracts import get_preset, validate_preset_for_template
from pipeline.prompts.curriculum import (
    build_curriculum_system_prompt,
    build_curriculum_user_prompt,
)
from pipeline.providers.registry import (
    get_node_text_model,
    get_node_text_route,
    get_node_text_spec,
)
from pipeline.state import PipelineError, StyleContext, TextbookPipelineState
from pipeline.types.requests import SectionPlan
from pipeline.llm_runner import run_llm


class CurriculumOutput(BaseModel):
    sections: list[SectionPlan]


def _build_style_context(state: TextbookPipelineState) -> StyleContext:
    preset = get_preset(state.request.preset_id)
    return StyleContext(
        preset_id=preset.id,
        palette=preset.palette,
        surface_style=preset.surface_style,
        density=preset.density,
        typography=preset.typography,
        template_id=state.contract.id,
        template_family=state.contract.family,
        interaction_level=state.contract.interaction_level,
        grade_band=state.request.grade_band,
        learner_fit=state.request.learner_fit,
    )


def _outline_from_seed(state: TextbookPipelineState) -> list[SectionPlan]:
    seed = state.request.seed_document
    if seed is None:
        return []

    sections = seed.sections
    outline: list[SectionPlan] = []
    for index, section in enumerate(sections, start=1):
        previous_title = sections[index - 2].header.title if index > 1 else None
        next_title = sections[index].header.title if index < len(sections) else None
        focus = section.header.objective or section.hook.headline or section.explanation.body
        outline.append(
            SectionPlan(
                section_id=section.section_id,
                title=section.header.title,
                position=index,
                focus=focus[:220],
                bridges_from=previous_title,
                bridges_to=next_title,
                needs_diagram=section.diagram is not None,
                needs_worked_example=(
                    section.worked_example is not None or bool(section.worked_examples)
                ),
            )
        )
    return outline


async def curriculum_planner(
    state: TextbookPipelineState | dict,
    *,
    provider_overrides: dict | None = None,
) -> dict:
    state = TextbookPipelineState.parse(state)

    if not validate_preset_for_template(state.contract.id, state.request.preset_id):
        return {
            "errors": [
                PipelineError(
                    node="curriculum_planner",
                    message=(
                        f"Preset '{state.request.preset_id}' is not allowed "
                        f"for template '{state.contract.id}'"
                    ),
                    recoverable=False,
                )
            ],
            "completed_nodes": ["curriculum_planner"],
        }

    style_context = _build_style_context(state)

    if state.request.seed_document is not None and state.request.seed_document.sections:
        return {
            "curriculum_outline": _outline_from_seed(state),
            "style_context": style_context,
            "completed_nodes": ["curriculum_planner"],
        }

    model = get_node_text_model(
        "curriculum_planner",
        provider_overrides,
        generation_mode=state.request.mode,
    )
    route = get_node_text_route(
        "curriculum_planner",
        generation_mode=state.request.mode,
    )
    spec = get_node_text_spec(
        "curriculum_planner",
        generation_mode=state.request.mode,
    )
    agent = Agent(
        model=model,
        output_type=CurriculumOutput,
        system_prompt=build_curriculum_system_prompt(
            template_id=state.contract.id,
            template_name=state.contract.name,
            template_family=state.contract.family,
        ),
    )

    try:
        result = await run_llm(
            generation_id=state.request.generation_id or "",
            node="curriculum_planner",
            route=route,
            spec=spec,
            agent=agent,
            user_prompt=build_curriculum_user_prompt(
                context=state.request.context,
                subject=state.request.subject,
                grade_band=state.request.grade_band,
                learner_fit=state.request.learner_fit,
                section_count=state.request.section_count,
            )
        )
        return {
            "curriculum_outline": result.output.sections,
            "style_context": style_context,
            "completed_nodes": ["curriculum_planner"],
        }
    except Exception as exc:
        return {
            "curriculum_outline": [],
            "style_context": style_context,
            "errors": [
                PipelineError(
                    node="curriculum_planner",
                    message=f"LLM call failed: {exc}",
                    recoverable=False,
                )
            ],
            "completed_nodes": ["curriculum_planner"],
        }
