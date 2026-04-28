from __future__ import annotations

from planning.models import (
    PlanValidationIssue,
    PlanValidationResult,
    PlanningSectionPlan,
    PlanningSectionRole,
)
from planning.role_maps import (
    ASSESSMENT_COMPONENTS,
    CHECK_COMPONENTS,
    PRACTICE_COMPONENTS,
    ROLE_COMPONENT_MAP,
    VISUAL_COMPONENTS,
)
from pipeline.contracts import get_section_field_for_component
from pipeline.resources import ResourceTemplate
from pipeline.types.requests import count_visual_placements
from pipeline.types.teacher_brief import TeacherBrief


def _issue(field: str | None, message: str, severity: str = "blocking") -> PlanValidationIssue:
    return PlanValidationIssue(field=field, message=message, severity=severity)


def _required_roles_present(brief: TeacherBrief, sections: list[PlanningSectionPlan]) -> tuple[bool, bool]:
    has_practice = any(
        section.role == "practice"
        or bool(set(section.selected_components).intersection(PRACTICE_COMPONENTS))
        for section in sections
    )
    has_check = any(
        section.role == "summary"
        or bool(set(section.selected_components).intersection(CHECK_COMPONENTS))
        or section.practice_target
        for section in sections
    )

    if brief.intended_outcome in {"practice", "assess"}:
        return has_practice, has_check
    if brief.intended_outcome in {"understand", "review", "compare", "vocabulary"}:
        return True, has_check
    return has_practice, has_check


def _obligation_satisfied(obligation: str, sections: list[PlanningSectionPlan]) -> bool:
    normalized = obligation.lower()
    roles = {section.role for section in sections}
    components = {
        component
        for section in sections
        for component in section.selected_components
    }

    if "student-facing work" in normalized or "student action" in normalized:
        return "practice" in roles or bool(components.intersection(PRACTICE_COMPONENTS))
    if "response item" in normalized or "assessable questions" in normalized:
        return bool(components.intersection(ASSESSMENT_COMPONENTS))
    if "understanding check" in normalized or "check" in normalized:
        return "summary" in roles or bool(components.intersection(CHECK_COMPONENTS))
    if "clear learning path" in normalized or "instructional sequence" in normalized:
        return "intro" in roles and any(role in roles for role in {"explain", "process", "timeline"})
    if "explanation" in normalized or "focused subtopic" in normalized:
        return any(role in roles for role in {"explain", "process", "compare", "timeline", "visual", "discover"})
    if "short" in normalized:
        return len(sections) <= 3
    return True


def _teacher_notes_issues(
    brief: TeacherBrief,
    sections: list[PlanningSectionPlan],
) -> list[PlanValidationIssue]:
    if not brief.teacher_notes:
        return []

    normalized = brief.teacher_notes.lower()
    visuals_requested = any(
        count_visual_placements(section) > 0
        or bool(set(section.selected_components).intersection(VISUAL_COMPONENTS))
        for section in sections
    )
    issues: list[PlanValidationIssue] = []
    if ("no visual" in normalized or "without visual" in normalized or "text only" in normalized) and visuals_requested:
        issues.append(
            _issue(
                "teacher_notes",
                "Teacher notes ask for no visuals, but the plan still includes visual-heavy sections.",
                "warning",
            )
        )
    if "step by step" in normalized and not any(section.role in {"process", "practice"} for section in sections):
        issues.append(
            _issue(
                "teacher_notes",
                "Teacher notes ask for step-by-step support, but the plan does not include a process or practice section.",
            )
        )
    return issues


def validate_plan(
    *,
    brief: TeacherBrief,
    template: ResourceTemplate,
    sections: list[PlanningSectionPlan],
    roles: list[PlanningSectionRole],
) -> PlanValidationResult:
    issues: list[PlanValidationIssue] = []
    depth_limit = template.depth_limits[brief.depth]
    allowed_role_set = set(roles)
    max_visuals = template.visual_policy.max_visuals_by_depth[brief.depth]

    if not (depth_limit.min_components <= len(sections) <= depth_limit.max_components):
        issues.append(
            _issue(
                "sections",
                (
                    f"Section count must stay between {depth_limit.min_components} and "
                    f"{depth_limit.max_components} for {template.label} at {brief.depth} depth."
                ),
            )
        )

    visual_count = 0
    for section in sections:
        if not section.selected_components:
            issues.append(
                _issue(
                    "selected_components",
                    f"Section {section.order} must include at least one selected component.",
                )
            )

        if section.role not in allowed_role_set:
            issues.append(
                _issue(
                    "role",
                    f"Section {section.order} uses forbidden role '{section.role}' for this brief.",
                )
            )

        allowed_components = set(ROLE_COMPONENT_MAP.get(section.role, ()))
        hallucinated_components = [
            component
            for component in section.selected_components
            if get_section_field_for_component(component) is None
        ]
        if hallucinated_components:
            issues.append(
                _issue(
                    "selected_components",
                    (
                        f"Section {section.order} selects unknown components: "
                        f"{', '.join(hallucinated_components)}."
                    ),
                )
            )

        invalid_components = [
            component
            for component in section.selected_components
            if component not in allowed_components and component not in hallucinated_components
        ]
        if invalid_components:
            issues.append(
                _issue(
                    "selected_components",
                    (
                        f"Section {section.order} selects components not allowed for role "
                        f"'{section.role}': {', '.join(invalid_components)}."
                    ),
                )
            )

        if section.role in {"visual", "discover"} and any(
            forbidden in template.forbidden_component_roles
            for forbidden in {"visualize", "guided_teaching_sequence"}
        ):
            issues.append(
                _issue(
                    "role",
                    f"Section {section.order} uses role '{section.role}' even though the resource forbids it.",
                )
            )

        if set(section.selected_components).intersection(VISUAL_COMPONENTS):
            visual_count += 1

    if visual_count > max_visuals:
        issues.append(
            _issue(
                "sections",
                f"Visual count exceeds the {max_visuals} visual limit for {template.label} at {brief.depth} depth.",
            )
        )

    for forbidden in template.forbidden_component_roles:
        forbidden_role = forbidden.strip().lower()
        if any(forbidden_role in section.role for section in sections):
            issues.append(
                _issue(
                    "role",
                    f"Forbidden role or role family '{forbidden}' appears in the plan.",
                )
            )

    for obligation in template.required_obligations:
        if not _obligation_satisfied(obligation, sections):
            issues.append(
                _issue(
                    "sections",
                    f"Plan does not satisfy required obligation: {obligation}",
                )
            )

    has_practice, has_check = _required_roles_present(brief, sections)
    if brief.intended_outcome in {"practice", "assess"} and not has_practice:
        issues.append(
            _issue(
                "sections",
                "This intended outcome requires at least one practice or question-focused section.",
            )
        )
    if not has_check:
        issues.append(
            _issue(
                "sections",
                "The plan needs a review, check, or wrap-up element that confirms understanding.",
            )
        )

    issues.extend(_teacher_notes_issues(brief, sections))

    return PlanValidationResult(
        is_valid=not any(issue.severity == "blocking" for issue in issues),
        issues=issues,
    )
