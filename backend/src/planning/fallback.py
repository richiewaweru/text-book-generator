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


def _depth_to_mode(depth: str) -> GenerationMode:
    if depth == "quick":
        return GenerationMode.DRAFT
    if depth == "deep":
        return GenerationMode.STRICT
    return GenerationMode.BALANCED


def _fallback_sections(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> list[PlanningSectionPlan]:
    depth_limit = template.depth_limits[brief.depth]
    section_count = max(depth_limit.min_components, min(len(roles), depth_limit.max_components))
    chosen_roles = roles[:section_count] or ["intro", "summary"]
    if section_count == 1:
        chosen_roles = ["summary"]
    elif section_count >= 2 and chosen_roles[-1] != "summary":
        chosen_roles[-1] = "summary"

    sections: list[PlanningSectionPlan] = []
    first_subtopic = brief.subtopics[0]
    for order, role in enumerate(chosen_roles, start=1):
        sections.append(
            PlanningSectionPlan(
                id=f"section-{uuid4().hex[:8]}",
                order=order,
                role=role,
                title={
                    "intro": f"Start {first_subtopic}",
                    "explain": f"Understand {first_subtopic}",
                    "practice": f"Practice {first_subtopic}",
                    "summary": f"Check {first_subtopic}",
                    "process": f"Steps in {first_subtopic}",
                    "compare": f"Compare {first_subtopic}",
                    "timeline": f"Timeline of {first_subtopic}",
                    "visual": f"See {first_subtopic}",
                    "discover": f"Explore {first_subtopic}",
                }[role],
                objective=f"Support the {template.label.lower()} using a safe fallback structure.",
                selected_components=list(ROLE_COMPONENT_MAP.get(role, ("explanation-block",)))[:2],
                rationale=f"Fallback section for role {role}.",
                practice_target="Confirm the learner can use the idea independently."
                if role == "practice"
                else None,
            )
        )
    return sections


def build_fallback_composition(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    roles: list[PlanningSectionRole],
) -> CompositionResult:
    return CompositionResult(
        sections=_fallback_sections(brief=brief, template=template, roles=roles),
        lesson_rationale=(
            f"This fallback keeps the {template.label.lower()} compact and centered on {', '.join(brief.subtopics)}."
        ),
        warning="Planning used a deterministic fallback. Review the structure before generating.",
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
