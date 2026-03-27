from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic_ai import Agent

from planning.models import (
    NormalizedBrief,
    PlanningRefinementOutput,
    PlanningSectionPlan,
    PlanningTemplateContract,
)

logger = logging.getLogger(__name__)


def _system_prompt() -> str:
    return "\n".join(
        [
            "You refine lesson-plan text only.",
            "You will receive a fixed lesson structure.",
            "Do not change section count, section order, role, components, or visual policy.",
            "Return valid JSON only.",
            "For each section, write a concise title and one-sentence rationale.",
            "Write a short lesson rationale for the teacher and an optional warning.",
        ]
    )


def _user_prompt(
    brief: NormalizedBrief,
    contract: PlanningTemplateContract,
    sections: list[PlanningSectionPlan],
) -> str:
    section_lines = "\n".join(
        f"- order={section.order} role={section.role} components={', '.join(section.selected_components) or 'none'} objective={section.objective or 'n/a'}"
        for section in sections
    )
    return "\n".join(
        [
            f"Intent: {brief.brief.intent}",
            f"Audience: {brief.brief.audience}",
            f"Prior knowledge: {brief.brief.prior_knowledge or 'none'}",
            f"Extra context: {brief.brief.extra_context or 'none'}",
            f"Template: {contract.name}",
            "Sections:",
            section_lines,
            "Return JSON with keys: lesson_rationale, warning, sections[{title, rationale}].",
        ]
    )


async def refine_plan_text(
    *,
    brief: NormalizedBrief,
    contract: PlanningTemplateContract,
    sections: list[PlanningSectionPlan],
    model: Any,
    run_llm_fn: Callable[..., Awaitable[Any]],
    generation_id: str = "",
    generation_mode: Any = "draft",
) -> PlanningRefinementOutput | None:
    agent = Agent(
        model=model,
        output_type=PlanningRefinementOutput,
        system_prompt=_system_prompt(),
    )
    user_prompt = _user_prompt(brief, contract, sections)

    for attempt in range(2):
        try:
            result = await run_llm_fn(
                generation_id=generation_id,
                node="brief_planner",
                agent=agent,
                model=model,
                user_prompt=user_prompt,
                generation_mode=generation_mode,
            )
            output = result.output
            if output is None or len(output.sections) != len(sections):
                raise ValueError("Planning refinement returned an unexpected section count.")
            return output
        except Exception as exc:
            logger.warning("Planning refinement attempt %s failed: %s", attempt + 1, exc)

    return None
