from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging
from typing import Any

import core.events as core_events
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from planning.llm_config import (
    PLANNING_VISUAL_ROUTER_CALLER,
    get_planning_slot,
)
from planning.models import (
    GenerationDirectives,
    PlanningSectionPlan,
    PlanningVisualIntent,
    PlanningVisualMode,
    VisualPolicy,
)
from planning.role_maps import ROLE_COMPONENT_MAP, VISUAL_COMPONENTS
from pipeline.types.requests import BlockVisualPlacement
from pipeline.types.teacher_brief import TeacherBrief
from resource_specs.schema import ResourceSpec

logger = logging.getLogger(__name__)


class _SectionVisualDecision(BaseModel):
    section_id: str
    required: bool = False
    intent: PlanningVisualIntent | None = None
    mode: PlanningVisualMode | None = None


class _VisualRoutingPlan(BaseModel):
    sections: list[_SectionVisualDecision] = Field(default_factory=list)


def _visual_intent(section: PlanningSectionPlan) -> PlanningVisualIntent:
    if section.role == "process":
        return "demonstrate_process"
    if section.role == "compare":
        return "compare_variants"
    if section.role in {"visual", "discover"}:
        return "show_realism"
    return "explain_structure"


def _visual_mode(brief: TeacherBrief, directives: GenerationDirectives, intent: str) -> PlanningVisualMode:
    _ = (brief, directives, intent)
    return "image"


def _derive_visual_placements(
    *,
    section: PlanningSectionPlan,
    intent: PlanningVisualIntent,
    should_visualize: bool,
) -> list[BlockVisualPlacement]:
    if not should_visualize:
        return []

    selected = set(section.selected_components)
    available = set(ROLE_COMPONENT_MAP.get(section.role, ()))
    block_target = "section" if section.role in {"visual", "discover"} else "explanation"

    if "diagram-compare" in selected or (intent == "compare_variants" and "diagram-compare" in available):
        return [
            BlockVisualPlacement(
                block=block_target,
                slot_type="diagram_compare",
                hint="Use a comparison visual." if block_target == "section" else "Use an explanation-adjacent comparison visual.",
            )
        ]

    if "diagram-series" in selected or (intent == "demonstrate_process" and "diagram-series" in available):
        return [
            BlockVisualPlacement(
                block=block_target,
                slot_type="diagram_series",
                hint="Use a sequence visual." if block_target == "section" else "Use an explanation-adjacent sequence visual.",
            )
        ]

    return [
        BlockVisualPlacement(
            block=block_target,
            slot_type="diagram",
            hint="Use a supporting diagram." if block_target == "section" else "Use an explanation-adjacent diagram.",
        )
    ]


def _system_prompt() -> str:
    return "\n".join(
        [
            "You decide where visuals are required in a classroom resource plan.",
            "Return valid JSON only.",
            "Only require visuals when they materially improve comprehension and fit the section's selected components.",
            "Schema fields:",
            '- sections [{"section_id": "string", "required": true, "intent": "string|null", "mode": "string|null"}]',
        ]
    )


def _user_prompt(
    brief: TeacherBrief,
    directives: GenerationDirectives,
    spec: ResourceSpec,
    sections: list[PlanningSectionPlan],
) -> str:
    section_lines = "\n".join(
        f"- id={section.id} role={section.role} components={', '.join(section.selected_components) or 'none'} objective={section.objective or 'n/a'}"
        for section in sections
    )
    return "\n".join(
        [
            f"Subject: {brief.subject}",
            f"Topic: {brief.topic}",
            f"Subtopics: {', '.join(brief.subtopics)}",
            f"Learner context: {brief.learner_context}",
            f"Supports: {', '.join(brief.supports) if brief.supports else 'none'}",
            f"Resource type: {brief.resource_type}",
            f"Visual limit for depth {brief.depth}: {getattr(spec.visuals, brief.depth)}",
            f"Allow diagrams: {spec.visuals.allow_diagrams}",
            f"Allow images: {spec.visuals.allow_images}",
            (
                "Directives: "
                f"reading_level={directives.reading_level}, explanation_style={directives.explanation_style}, "
                f"scaffold_level={directives.scaffold_level}"
            ),
            "Sections:",
            section_lines,
        ]
    )


async def _resolve_with_llm(
    brief: TeacherBrief,
    directives: GenerationDirectives,
    spec: ResourceSpec,
    sections: list[PlanningSectionPlan],
    *,
    model: Any | None,
    run_llm_fn: Callable[..., Awaitable[Any]] | None,
    generation_id: str,
) -> dict[str, _SectionVisualDecision] | None:
    if model is None or run_llm_fn is None:
        return None

    agent = Agent(
        model=model,
        output_type=_VisualRoutingPlan,
        system_prompt=_system_prompt(),
    )
    result = await run_llm_fn(
        trace_id=generation_id,
        caller=PLANNING_VISUAL_ROUTER_CALLER,
        agent=agent,
        model=model,
        user_prompt=_user_prompt(brief, directives, spec, sections),
        slot=get_planning_slot(PLANNING_VISUAL_ROUTER_CALLER),
    )
    output = result.output
    if output is None or len(output.sections) != len(sections):
        return None
    return {section.section_id: section for section in output.sections}


async def route_visuals(
    brief: TeacherBrief,
    directives: GenerationDirectives,
    spec: ResourceSpec,
    sections: list[PlanningSectionPlan],
    *,
    model: Any | None = None,
    run_llm_fn: Callable[..., Awaitable[Any]] | None = None,
    generation_id: str = "",
) -> list[PlanningSectionPlan]:
    llm_decisions = await _resolve_with_llm(
        brief,
        directives,
        spec,
        sections,
        model=model,
        run_llm_fn=run_llm_fn,
        generation_id=generation_id,
    )
    allow_visuals = "visuals" in brief.supports or spec.visuals.allow_diagrams
    max_visuals = getattr(spec.visuals, brief.depth)
    committed_visuals = 0

    for section in sections:
        decision = llm_decisions.get(section.id) if llm_decisions is not None else None
        intent = (decision.intent if decision else None) or _visual_intent(section)
        mode = (decision.mode if decision else None) or _visual_mode(brief, directives, intent)
        component_visual = bool(set(section.selected_components).intersection(VISUAL_COMPONENTS))
        role_visual = section.role in {"visual", "compare", "process", "discover"}
        should_visualize = bool(
            allow_visuals
            and committed_visuals < max_visuals
            and (
                (decision.required if decision else False)
                or component_visual
                or role_visual
            )
        )
        placements = _derive_visual_placements(
            section=section,
            intent=intent,
            should_visualize=should_visualize,
        )
        if placements:
            committed_visuals += 1
        section.visual_placements = placements
        section.visual_policy = VisualPolicy(
            required=bool(placements),
            intent=intent if placements else None,
            mode=mode if placements else None,
            goal={
                "demonstrate_process": "Show the sequence or method clearly enough that the learner can follow each step.",
                "compare_variants": "Put the alternatives in view so the learner can spot the difference that matters.",
                "show_realism": "Ground the section in a realistic visual anchor the learner can point at.",
                "explain_structure": "Show the important structure or relationship the section is describing.",
            }[intent]
            if placements
            else None,
            style_notes=(
                "Clean structural diagram, labeled nodes, clear arrows."
                if mode == "svg"
                else "Classroom-friendly educational image, accurate labels, no decorative clutter."
            )
            if placements
            else None,
        )
        if generation_id:
            core_events.event_bus.publish(
                generation_id,
                {
                    "type": "visual_placements_committed",
                    "generation_id": generation_id,
                    "section_id": section.id,
                    "placements_count": len(placements),
                    "placements_summary": [
                        f"{placement.block}:{placement.slot_type}:{placement.sizing}"
                        for placement in placements
                    ],
                },
            )

    return sections
