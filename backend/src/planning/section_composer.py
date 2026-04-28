from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from pydantic_ai import Agent

from planning.llm_config import (
    PLANNING_SECTION_COMPOSER_CALLER,
    get_planning_slot,
)
from planning.models import (
    CompositionResult,
    GenerationDirectives,
    PlanningSectionPlan,
    PlanningSectionRole,
    SectionGenerationNotes,
)
from planning.role_maps import ROLE_COMPONENT_MAP
from pipeline.resources import ResourceTemplate
from pipeline.types.teacher_brief import TeacherBrief


def _build_section(
    *,
    order: int,
    role: PlanningSectionRole,
    components: list[str],
    title: str,
    objective: str,
    rationale: str,
) -> PlanningSectionPlan:
    return PlanningSectionPlan(
        id=f"section-{uuid4().hex[:8]}",
        order=order,
        role=role,
        title=title,
        objective=objective,
        selected_components=components,
        rationale=rationale,
        generation_notes=_generation_notes(role),
        practice_target="Check whether the learner can apply the idea independently."
        if role == "practice"
        else None,
    )


def _generation_notes(role: PlanningSectionRole) -> SectionGenerationNotes | None:
    if role == "practice":
        return SectionGenerationNotes(brevity_override="tight")
    if role == "summary":
        return SectionGenerationNotes(
            brevity_override="tight",
            tone_override="clear and conclusive",
        )
    return None


def _section_objective(role: PlanningSectionRole, brief: TeacherBrief) -> str:
    objectives = {
        "intro": f"Open the {brief.subtopic} resource clearly and make the learning target obvious.",
        "explain": f"Explain the core idea in {brief.subtopic} using accessible language.",
        "practice": f"Let the learner use {brief.subtopic} independently or with light support.",
        "summary": f"Close the resource by checking the main takeaway from {brief.subtopic}.",
        "process": f"Break {brief.subtopic} into repeatable steps.",
        "compare": f"Keep the important differences inside {brief.subtopic} visible.",
        "timeline": f"Show the sequence or chronology inside {brief.subtopic}.",
        "visual": f"Use a visual anchor to support understanding of {brief.subtopic}.",
        "discover": f"Guide learners to notice the pattern inside {brief.subtopic}.",
    }
    return objectives[role]


def _fallback_title(role: PlanningSectionRole, brief: TeacherBrief, order: int) -> str:
    titles = {
        "intro": f"Getting Started with {brief.subtopic}",
        "explain": f"Understanding {brief.subtopic}",
        "practice": f"Try {brief.subtopic}",
        "summary": f"Check {brief.subtopic}",
        "process": f"Steps for {brief.subtopic}",
        "compare": f"Compare {brief.subtopic}",
        "timeline": f"Sequence of {brief.subtopic}",
        "visual": f"See {brief.subtopic}",
        "discover": f"Explore {brief.subtopic}",
    }
    return titles.get(role, f"Section {order}")


def build_deterministic_composition(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> CompositionResult:
    depth_limit = template.depth_limits[brief.depth]
    section_count = max(depth_limit.min_components, min(len(roles), depth_limit.max_components))
    chosen_roles = roles[:section_count] or ["intro", "summary"]

    sections = [
        _build_section(
            order=index,
            role=role,
            components=list(ROLE_COMPONENT_MAP.get(role, ("explanation-block",)))[:2],
            title=_fallback_title(role, brief, index),
            objective=_section_objective(role, brief),
            rationale=f"This section uses the {role} role to support the {template.label} resource shape.",
        )
        for index, role in enumerate(chosen_roles, start=1)
    ]
    return CompositionResult(
        sections=sections,
        lesson_rationale=(
            f"This {template.label.lower()} follows the selected {brief.resource_type} shape and "
            f"keeps the focus on {brief.subtopic}."
        ),
        warning=None,
    )


def _system_prompt() -> str:
    return "\n".join(
        [
            "You compose a reviewed classroom resource plan from a structured teacher brief.",
            "Return JSON only.",
            "Do not write lesson content.",
            "Use only the allowed planning roles and allowed components for each role.",
            "Keep section count within the stated depth limits.",
            "Titles must be clear and student-facing.",
            "Every section must include at least one selected component.",
        ]
    )


def _role_component_lines(roles: list[PlanningSectionRole]) -> str:
    return "\n".join(
        f"- {role}: {', '.join(ROLE_COMPONENT_MAP.get(role, ())) or 'none'}"
        for role in roles
    )


def _user_prompt(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
    directives: GenerationDirectives,
    repair_instructions: list[str] | None,
) -> str:
    depth_limit = template.depth_limits[brief.depth]
    parts = [
        f"Subject: {brief.subject}",
        f"Topic: {brief.topic}",
        f"Subtopic: {brief.subtopic}",
        f"Learner context: {brief.learner_context}",
        f"Intended outcome: {brief.intended_outcome}",
        f"Resource type: {brief.resource_type}",
        f"Depth: {brief.depth}",
        f"Supports: {', '.join(brief.supports) if brief.supports else 'none'}",
        f"Teacher notes: {brief.teacher_notes or 'none'}",
        f"Template label: {template.label}",
        f"Template description: {template.description}",
        f"Required obligations: {'; '.join(template.required_obligations) or 'none'}",
        (
            "Depth limits: "
            f"min sections {depth_limit.min_components}, max sections {depth_limit.max_components}, "
            f"target time {depth_limit.target_time_minutes}, "
            f"question range {depth_limit.question_count_range or 'n/a'}"
        ),
        (
            "Directives: "
            f"tone={directives.tone_profile}, reading_level={directives.reading_level}, "
            f"explanation_style={directives.explanation_style}, example_style={directives.example_style}, "
            f"scaffold_level={directives.scaffold_level}, brevity={directives.brevity}"
        ),
        f"Resolved planning roles: {', '.join(roles)}",
        "Role component map:",
        _role_component_lines(roles),
        "Return this JSON shape exactly:",
        "{",
        '  "lesson_rationale": "string",',
        '  "warning": "string|null",',
        '  "sections": [',
        "    {",
        '      "id": "section-unique",',
        '      "order": 1,',
        '      "role": "intro|explain|practice|summary|process|compare|timeline|visual|discover",',
        '      "title": "string",',
        '      "objective": "string",',
        '      "focus_note": "string|null",',
        '      "selected_components": ["component-id"],',
        '      "rationale": "string",',
        '      "terms_to_define": ["optional"],',
        '      "terms_assumed": ["optional"],',
        '      "practice_target": "string|null"',
        "    }",
        "  ]",
        "}",
    ]
    if repair_instructions:
        parts.extend(
            [
                "Repair instructions:",
                *[f"- {instruction}" for instruction in repair_instructions],
            ]
        )
    return "\n".join(parts)


async def compose_sections(
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
    directives: GenerationDirectives,
    *,
    model: Any | None = None,
    run_llm_fn: Callable[..., Awaitable[Any]] | None = None,
    generation_id: str = "",
    repair_instructions: list[str] | None = None,
) -> CompositionResult:
    if model is None or run_llm_fn is None:
        return build_deterministic_composition(brief=brief, template=template, roles=roles)

    agent = Agent(
        model=model,
        output_type=CompositionResult,
        system_prompt=_system_prompt(),
    )
    result = await run_llm_fn(
        trace_id=generation_id,
        caller=PLANNING_SECTION_COMPOSER_CALLER,
        agent=agent,
        model=model,
        user_prompt=_user_prompt(
            brief=brief,
            template=template,
            roles=roles,
            directives=directives,
            repair_instructions=repair_instructions,
        ),
        slot=get_planning_slot(PLANNING_SECTION_COMPOSER_CALLER),
    )
    output = result.output
    if output is None:
        raise ValueError("Planning section composer returned no structured output.")
    return output
