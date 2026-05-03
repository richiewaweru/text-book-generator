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
from pipeline.types.teacher_brief import TeacherBrief
from resource_specs.schema import ResourceSpec
from resource_specs.renderer import render_spec_for_prompt


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
    joined_subtopics = ", ".join(brief.subtopics)
    objectives = {
        "intro": f"Open the {joined_subtopics} resource clearly and make the learning target obvious.",
        "explain": f"Explain the core idea in {joined_subtopics} using accessible language.",
        "practice": f"Let the learner use {joined_subtopics} independently or with light support.",
        "summary": f"Close the resource by checking the main takeaway from {joined_subtopics}.",
        "process": f"Break {joined_subtopics} into repeatable steps.",
        "compare": f"Keep the important differences inside {joined_subtopics} visible.",
        "timeline": f"Show the sequence or chronology inside {joined_subtopics}.",
        "visual": f"Use a visual anchor to support understanding of {joined_subtopics}.",
        "discover": f"Guide learners to notice the pattern inside {joined_subtopics}.",
    }
    return objectives[role]


def _fallback_title(role: PlanningSectionRole, brief: TeacherBrief, order: int) -> str:
    first_subtopic = brief.subtopics[0]
    titles = {
        "intro": f"Getting Started with {first_subtopic}",
        "explain": f"Understanding {first_subtopic}",
        "practice": f"Try {first_subtopic}",
        "summary": f"Check {first_subtopic}",
        "process": f"Steps for {first_subtopic}",
        "compare": f"Compare {first_subtopic}",
        "timeline": f"Sequence of {first_subtopic}",
        "visual": f"See {first_subtopic}",
        "discover": f"Explore {first_subtopic}",
    }
    return titles.get(role, f"Section {order}")


def build_deterministic_composition(
    *,
    brief: TeacherBrief,
    spec: ResourceSpec,
    roles: list[PlanningSectionRole],
) -> CompositionResult:
    depth_limit = spec.depth_limit(brief.depth)
    section_count = max(depth_limit.min_sections, min(len(roles), depth_limit.max_sections))
    chosen_roles = roles[:section_count] or ["intro", "summary"]

    sections = [
        _build_section(
            order=index,
            role=role,
            components=list(ROLE_COMPONENT_MAP.get(role, ("explanation-block",)))[:2],
            title=_fallback_title(role, brief, index),
            objective=_section_objective(role, brief),
            rationale=f"This section uses the {role} role to support the {spec.label} resource shape.",
        )
        for index, role in enumerate(chosen_roles, start=1)
    ]
    return CompositionResult(
        sections=sections,
        lesson_rationale=(
            f"This {spec.label.lower()} follows the selected {brief.resource_type} shape and "
            f"keeps the focus on {', '.join(brief.subtopics)}."
        ),
        warning=None,
    )


def _system_prompt() -> str:
    return "\n".join(
        [
            "You compose a classroom resource plan from a structured teacher brief.",
            "",
            "The resource spec below is a HARD CONSTRAINT document - not a suggestion.",
            "Forbidden components are NEVER selected regardless of role, content, or any other consideration.",
            "Treat every rule in the spec as absolute. Do not override it.",
            "",
            "Return JSON only.",
            "Do not write lesson content.",
            "Keep section count within the stated depth limits.",
            "Titles must be clear and student-facing.",
            "Every section must include at least one selected component.",
            "Each section should explain one focused idea.",
            "Do not create thin sections that cannot stand alone.",
            "If multiple subtopics do not fit cleanly, consolidate related ones and explain that in warning.",
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
    spec: ResourceSpec,
    roles: list[PlanningSectionRole],
    directives: GenerationDirectives,
    repair_instructions: list[str] | None,
) -> str:
    depth_limit = spec.depth_limit(brief.depth)
    class_profile = brief.class_profile
    spec_block = render_spec_for_prompt(
        spec=spec,
        depth=brief.depth,
        active_roles=list(roles),
        active_supports=list(brief.supports),
    )
    parts = [
        f"Subject: {brief.subject}",
        f"Topic: {brief.topic}",
        f"Subtopics: {', '.join(brief.subtopics)}",
        f"Grade level: {brief.grade_level}",
        f"Grade band: {brief.grade_band}",
        (
            "Class profile: "
            f"reading={class_profile.reading_level}, "
            f"language={class_profile.language_support}, "
            f"confidence={class_profile.confidence}, "
            f"prior_knowledge={class_profile.prior_knowledge}, "
            f"pacing={class_profile.pacing}, "
            f"preferences={', '.join(class_profile.learning_preferences) or 'none'}"
        ),
        f"Learner context: {brief.learner_context}",
        f"Intended outcome: {brief.intended_outcome}",
        f"Resource type: {brief.resource_type}",
        f"Depth: {brief.depth}",
        f"Supports: {', '.join(brief.supports) if brief.supports else 'none'}",
        f"Teacher notes: {brief.teacher_notes or 'none'}",
        spec_block,
        (
            "Depth limits: "
            f"min sections {depth_limit.min_sections}, max sections {depth_limit.max_sections}, "
            f"target time {depth_limit.time_minutes}, "
            f"question range {depth_limit.questions or 'n/a'}"
        ),
        (
            "Directives: "
            f"tone={directives.tone_profile}, reading_level={directives.reading_level}, "
            f"explanation_style={directives.explanation_style}, example_style={directives.example_style}, "
            f"scaffold_level={directives.scaffold_level}, brevity={directives.brevity}"
        ),
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
    spec: ResourceSpec,
    roles: list[PlanningSectionRole],
    directives: GenerationDirectives,
    *,
    model: Any | None = None,
    run_llm_fn: Callable[..., Awaitable[Any]] | None = None,
    generation_id: str = "",
    repair_instructions: list[str] | None = None,
) -> CompositionResult:
    if model is None or run_llm_fn is None:
        return build_deterministic_composition(brief=brief, spec=spec, roles=roles)

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
            spec=spec,
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
