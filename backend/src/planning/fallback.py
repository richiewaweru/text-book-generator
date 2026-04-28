from __future__ import annotations

from uuid import uuid4

from planning.models import (
    CompositionResult,
    GenerationDirectives,
    PlanningGenerationSpec,
    PlanningSectionPlan,
    PlanningSectionRole,
    TemplateDecision,
)
from planning.role_maps import ROLE_COMPONENT_MAP
from pipeline.resources import ResourceTemplate
from pipeline.types.requests import GenerationMode
from pipeline.types.teacher_brief import TeacherBrief

_RUNTIME_TEMPLATE_ID = "guided-concept-path"
_RUNTIME_PRESET_ID = "blue-classroom"
_CONTENT_BEARING_ROLES = frozenset(
    {"explain", "process", "visual", "discover", "compare", "timeline"}
)


def _depth_to_mode(depth: str) -> GenerationMode:
    if depth == "quick":
        return GenerationMode.DRAFT
    if depth == "deep":
        return GenerationMode.STRICT
    return GenerationMode.BALANCED


def _audience_prefix(brief: TeacherBrief) -> str:
    return brief.grade_level.replace("_", " ").title()


def _choose_roles(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> list[PlanningSectionRole]:
    depth_limit = template.depth_limits[brief.depth]
    section_count = max(
        depth_limit.min_components,
        min(len(roles), depth_limit.max_components),
    )
    chosen_roles = roles[:section_count] or ["intro", "summary"]
    if section_count == 1:
        return ["summary"]
    if section_count >= 2 and chosen_roles[-1] != "summary":
        chosen_roles[-1] = "summary"
    return chosen_roles


def _group_subtopics(subtopics: list[str], group_count: int) -> list[list[str]]:
    groups: list[list[str]] = [[] for _ in range(group_count)]
    for index, subtopic in enumerate(subtopics):
        groups[index % group_count].append(subtopic)
    return groups


def _assign_subtopics_to_sections(
    roles: list[PlanningSectionRole],
    subtopics: list[str],
) -> list[str | None]:
    assignments: list[str | None] = [None] * len(roles)
    slot_indexes = [index for index, role in enumerate(roles) if role in _CONTENT_BEARING_ROLES]

    if not slot_indexes:
        return assignments

    if len(subtopics) <= len(slot_indexes):
        for slot_index, subtopic in zip(slot_indexes, subtopics):
            assignments[slot_index] = subtopic
        return assignments

    groups = _group_subtopics(subtopics, len(slot_indexes))
    for slot_index, group in zip(slot_indexes, groups):
        assignments[slot_index] = " + ".join(group)
    return assignments


def _format_subtopic_list(subtopics: list[str]) -> str:
    if not subtopics:
        return ""
    if len(subtopics) == 1:
        return subtopics[0]
    return ", ".join(subtopics)


def _title_for_role(
    brief: TeacherBrief,
    role: PlanningSectionRole,
    *,
    role_focus: str,
) -> str:
    prefix = _audience_prefix(brief)
    return {
        "intro": f"{prefix} start: {role_focus}",
        "explain": f"{prefix} understand {role_focus}",
        "practice": f"{prefix} practice {role_focus}",
        "summary": f"{prefix} check {role_focus}",
        "process": f"{prefix} steps in {role_focus}",
        "compare": f"{prefix} compare {role_focus}",
        "timeline": f"{prefix} timeline of {role_focus}",
        "visual": f"{prefix} see {role_focus}",
        "discover": f"{prefix} explore {role_focus}",
    }[role]


def _continuity_focus(
    role: PlanningSectionRole,
    topic: str,
    covered_focus: str,
) -> str:
    if role == "intro":
        return topic
    if role == "practice":
        return covered_focus
    if role == "summary":
        return covered_focus
    return topic


def _section_objective(
    brief: TeacherBrief,
    role: PlanningSectionRole,
    *,
    role_focus: str,
) -> str:
    learner_context = brief.learner_context
    if role in _CONTENT_BEARING_ROLES:
        return f"Cover {role_focus} for {learner_context}."
    if role == "intro":
        return f"Orient learners to {role_focus} for {learner_context}."
    if role == "practice":
        return f"Help learners apply {role_focus} with confidence."
    if role == "summary":
        return f"Consolidate {role_focus} for {learner_context}."
    return (
        f"Support a {brief.grade_level.replace('_', ' ')} class with "
        f"{brief.class_profile.confidence} confidence and {brief.class_profile.pacing} pacing."
    )


def _practice_target(covered_subtopics: list[str]) -> str:
    if covered_subtopics:
        return f"Confirm the learner can apply: {', '.join(covered_subtopics)}."
    return "Confirm the learner can use the idea independently."


def _fallback_sections(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> list[PlanningSectionPlan]:
    chosen_roles = _choose_roles(brief=brief, template=template, roles=roles)
    subtopics = list(brief.subtopics or [brief.topic])
    assignments = _assign_subtopics_to_sections(chosen_roles, subtopics)
    covered_subtopics = [assignment for assignment in assignments if assignment]
    covered_focus = _format_subtopic_list(covered_subtopics or subtopics)

    sections: list[PlanningSectionPlan] = []
    single_subtopic = len(subtopics) == 1
    for order, (role, assignment) in enumerate(zip(chosen_roles, assignments), start=1):
        if single_subtopic:
            role_focus = subtopics[0]
            focus_note = subtopics[0]
        elif assignment:
            role_focus = assignment
            focus_note = assignment
        else:
            role_focus = _continuity_focus(role, brief.topic, covered_focus)
            focus_note = None

        sections.append(
            PlanningSectionPlan(
                id=f"section-{uuid4().hex[:8]}",
                order=order,
                role=role,
                title=_title_for_role(brief, role, role_focus=role_focus),
                objective=_section_objective(brief, role, role_focus=role_focus),
                focus_note=focus_note,
                selected_components=list(ROLE_COMPONENT_MAP.get(role, ("explanation-block",)))[:2],
                rationale=(
                    f"Fallback section for role {role} tuned for "
                    f"{brief.class_profile.reading_level} reading and "
                    f"{brief.class_profile.prior_knowledge} prior knowledge."
                ),
                practice_target=_practice_target(covered_subtopics) if role == "practice" else None,
            )
        )
    return sections


def _fallback_warning(
    *,
    brief: TeacherBrief,
    roles: list[PlanningSectionRole],
) -> str:
    subtopics = list(brief.subtopics or [brief.topic])
    slot_count = sum(1 for role in roles if role in _CONTENT_BEARING_ROLES)
    if slot_count > 0 and len(subtopics) > slot_count:
        return (
            "Planning used a deterministic fallback. "
            f"{len(subtopics)} subtopics were condensed into {slot_count} "
            "content section(s). Review the structure before generating."
        )
    return "Planning used a deterministic fallback. Review the structure before generating."


def build_fallback_composition(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> CompositionResult:
    chosen_roles = _choose_roles(brief=brief, template=template, roles=roles)
    subtopics = list(brief.subtopics or [brief.topic])
    return CompositionResult(
        sections=_fallback_sections(brief=brief, template=template, roles=roles),
        lesson_rationale=(
            f"This fallback keeps the {template.label.lower()} compact and centered on "
            f"{', '.join(subtopics)}."
        ),
        warning=_fallback_warning(brief=brief, roles=chosen_roles),
    )


def build_fallback_spec(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
    directives: GenerationDirectives,
    generation_id: str = "",
) -> PlanningGenerationSpec:
    composition = build_fallback_composition(brief=brief, template=template, roles=roles)
    return PlanningGenerationSpec(
        id=generation_id or uuid4().hex,
        template_id=_RUNTIME_TEMPLATE_ID,
        preset_id=_RUNTIME_PRESET_ID,
        mode=_depth_to_mode(brief.depth),
        template_decision=TemplateDecision(
            chosen_id=brief.resource_type,
            chosen_name=template.label,
            rationale=f"Teacher selected {template.label}.",
            fit_score=1.0,
            alternatives=[],
        ),
        lesson_rationale=composition.lesson_rationale,
        directives=directives,
        committed_budgets={},
        sections=composition.sections,
        warning=composition.warning,
        source_brief_id=uuid4().hex,
        source_brief=brief,
        status="draft",
    )
