from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from planning.fallback import build_fallback_composition, build_fallback_spec
from planning.models import (
    GenerationDirectives,
    PlanningGenerationSpec,
    PlanningSectionRole,
    TemplateDecision,
)
from planning.plan_validator import validate_plan
from planning.role_maps import (
    OUTCOME_ROLE_MAP,
    SUPPORT_ROLE_MAP,
    TEMPLATE_ROLE_TO_SECTION_ROLE,
)
from planning.section_composer import compose_sections
from planning.visual_router import route_visuals
from pipeline.resources import get_resource_template
from pipeline.types.requests import GenerationMode
from pipeline.types.teacher_brief import TeacherBrief

PlanningEvent = dict[str, object]
PlanningEmitter = Callable[[PlanningEvent], Awaitable[None] | None]
_RUNTIME_TEMPLATE_ID = "guided-concept-path"
_RUNTIME_PRESET_ID = "blue-classroom"
def _depth_to_mode(depth: str) -> GenerationMode:
    if depth == "quick":
        return GenerationMode.DRAFT
    if depth == "deep":
        return GenerationMode.STRICT
    return GenerationMode.BALANCED


def _resolve_directives(brief: TeacherBrief) -> GenerationDirectives:
    profile = brief.class_profile
    reading_level = (
        "simple"
        if (
            profile.reading_level == "below_grade"
            or profile.language_support in {"some_ell", "many_ell"}
            or "simpler_reading" in brief.supports
        )
        else "standard"
    )
    explanation_style = (
        "concrete-first"
        if (
            profile.prior_knowledge == "new_topic"
            or profile.confidence == "low"
            or "step_by_step" in brief.supports
        )
        else "balanced"
    )
    scaffold_level = (
        "high"
        if (
            profile.reading_level == "below_grade"
            or profile.confidence == "low"
            or profile.pacing == "short_chunks"
            or "step_by_step" in brief.supports
        )
        else "medium"
    )
    return GenerationDirectives(
        tone_profile="supportive",
        reading_level=reading_level,
        explanation_style=explanation_style,
        example_style="everyday",
        scaffold_level=scaffold_level,
        brevity={
            "quick": "tight",
            "standard": "balanced",
            "deep": "expanded",
        }[brief.depth],
    )


def _resolve_roles(brief: TeacherBrief) -> list[PlanningSectionRole]:
    template = get_resource_template(brief.resource_type)
    allowed_template_roles = [
        *template.recommended_component_roles,
        *template.optional_component_roles,
    ]
    allowed_roles = [
        TEMPLATE_ROLE_TO_SECTION_ROLE[role]
        for role in allowed_template_roles
        if role in TEMPLATE_ROLE_TO_SECTION_ROLE
    ]

    requested_template_roles = [
        *OUTCOME_ROLE_MAP.get(brief.intended_outcome, ()),
        *(
            role
            for support in brief.supports
            for role in SUPPORT_ROLE_MAP.get(support, ())
        ),
    ]

    resolved: list[PlanningSectionRole] = []
    for template_role in requested_template_roles:
        section_role = TEMPLATE_ROLE_TO_SECTION_ROLE.get(template_role)
        if section_role is None or section_role not in allowed_roles:
            continue
        if section_role not in resolved:
            resolved.append(section_role)

    if "intro" not in resolved:
        resolved.insert(0, "intro")
    if "summary" not in resolved:
        resolved.append("summary")

    for fallback_role in allowed_roles:
        if fallback_role not in resolved:
            resolved.append(fallback_role)

    return resolved


class PlanningService:
    async def plan(
        self,
        brief: TeacherBrief,
        *,
        model: Any,
        run_llm_fn: Callable[..., Awaitable[Any]],
        generation_id: str = "",
        emit: PlanningEmitter | None = None,
    ) -> PlanningGenerationSpec:
        template = get_resource_template(brief.resource_type)
        directives = _resolve_directives(brief)
        roles = _resolve_roles(brief)

        composition_result = await compose_sections(
            brief,
            template,
            roles,
            directives,
            model=model,
            run_llm_fn=run_llm_fn,
            generation_id=generation_id,
        )
        validation = validate_plan(
            brief=brief,
            template=template,
            sections=composition_result.sections,
            roles=roles,
        )

        if not validation.is_valid:
            composition_result = await compose_sections(
                brief,
                template,
                roles,
                directives,
                model=model,
                run_llm_fn=run_llm_fn,
                generation_id=generation_id,
                repair_instructions=[issue.message for issue in validation.issues],
            )
            validation = validate_plan(
                brief=brief,
                template=template,
                sections=composition_result.sections,
                roles=roles,
            )

        used_fallback = False
        if not validation.is_valid:
            composition_result = build_fallback_composition(
                brief=brief,
                template=template,
                roles=roles,
            )
            used_fallback = True

        sections = await route_visuals(
            brief,
            directives,
            template,
            composition_result.sections,
            model=model,
            run_llm_fn=run_llm_fn,
            generation_id=generation_id,
        )

        warning = composition_result.warning
        if validation.issues and not used_fallback:
            warning_messages = [issue.message for issue in validation.issues if issue.severity == "warning"]
            if warning_messages:
                warning = warning or " ".join(warning_messages)

        spec = PlanningGenerationSpec(
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
            lesson_rationale=composition_result.lesson_rationale,
            directives=directives,
            committed_budgets={},
            sections=sections,
            warning=warning,
            source_brief_id=uuid4().hex,
            source_brief=brief,
            status="draft",
        )

        if emit is not None:
            maybe_result = emit(
                {
                    "event": "plan_complete",
                    "data": {"spec": spec.model_dump(mode="json")},
                }
            )
            if maybe_result is not None:
                await maybe_result

        return spec

    def fallback(
        self,
        brief: TeacherBrief,
        *,
        generation_id: str = "",
    ) -> PlanningGenerationSpec:
        template = get_resource_template(brief.resource_type)
        return build_fallback_spec(
            brief=brief,
            template=template,
            roles=_resolve_roles(brief),
            directives=_resolve_directives(brief),
            generation_id=generation_id,
        )
