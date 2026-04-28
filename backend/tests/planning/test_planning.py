from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from planning.models import CompositionResult, PlanningSectionPlan
from planning.plan_validator import validate_plan
from planning.service import PlanningService, _resolve_directives, _resolve_roles
from pipeline.resources import get_resource_template
from pipeline.types.teacher_brief import TeacherBrief


def build_brief(**overrides) -> TeacherBrief:
    payload = {
        "subject": "Math",
        "topic": "Algebra",
        "subtopic": "Solving two-step equations",
        "learner_context": "Grade 7 mixed levels",
        "intended_outcome": "practice",
        "resource_type": "worksheet",
        "supports": ["worked_examples", "step_by_step"],
        "depth": "standard",
        "teacher_notes": "Keep the language simple.",
    }
    payload.update(overrides)
    return TeacherBrief.model_validate(payload)


def build_sections() -> list[PlanningSectionPlan]:
    return [
        PlanningSectionPlan(
            id="section-1",
            order=1,
            role="intro",
            title="Start with the idea",
            objective="Open the resource clearly.",
            selected_components=["hook-hero"],
            rationale="Open with a focused hook.",
        ),
        PlanningSectionPlan(
            id="section-2",
            order=2,
            role="practice",
            title="Try the method",
            objective="Let learners apply the steps.",
            selected_components=["practice-stack", "short-answer"],
            rationale="Move quickly into guided practice.",
            practice_target="Solve two-step equations independently.",
        ),
        PlanningSectionPlan(
            id="section-3",
            order=3,
            role="summary",
            title="Check understanding",
            objective="Confirm the learner can explain the steps.",
            selected_components=["summary-block", "reflection-prompt"],
            rationale="Close with a check.",
        ),
    ]


def test_resolve_directives_uses_struggling_reader_markers() -> None:
    directives = _resolve_directives(
        build_brief(
            learner_context="Grade 7 students, low confidence and below grade reading",
            supports=["step_by_step"],
            depth="quick",
        )
    )

    assert directives.reading_level == "simple"
    assert directives.explanation_style == "concrete-first"
    assert directives.scaffold_level == "high"
    assert directives.brevity == "tight"


def test_resolve_roles_filters_to_resource_template() -> None:
    roles = _resolve_roles(
        build_brief(
            intended_outcome="assess",
            resource_type="quiz",
            supports=["visuals", "challenge_questions"],
        )
    )

    assert "intro" in roles
    assert "summary" in roles
    assert "practice" in roles
    assert "visual" in roles
    assert "compare" not in roles


def test_validate_plan_rejects_invalid_components() -> None:
    brief = build_brief()
    template = get_resource_template(brief.resource_type)
    invalid_sections = [
        PlanningSectionPlan(
            id="section-1",
            order=1,
            role="intro",
            title="Bad intro",
            objective="Open the lesson.",
            selected_components=["practice-stack"],
            rationale="Invalid component for intro.",
        )
    ]

    result = validate_plan(
        brief=brief,
        template=template,
        sections=invalid_sections,
        roles=["intro", "practice", "summary"],
    )

    assert result.is_valid is False
    assert any("not allowed for role" in issue.message for issue in result.issues)


async def test_planning_service_retries_then_preserves_runtime_template_id() -> None:
    brief = build_brief()
    valid_composition = CompositionResult(
        sections=build_sections(),
        lesson_rationale="A short worksheet that introduces the method and checks it.",
        warning=None,
    )
    invalid_composition = CompositionResult(
        sections=[
            PlanningSectionPlan(
                id="section-1",
                order=1,
                role="intro",
                title="Broken",
                objective="Broken",
                selected_components=[],
                rationale="Broken",
            )
        ],
        lesson_rationale="Broken plan",
        warning=None,
    )
    calls: list[dict] = []

    async def fake_compose(*args, **kwargs):
        calls.append(kwargs)
        return invalid_composition if len(calls) == 1 else valid_composition

    async def fake_route_visuals(brief, directives, template, sections, **kwargs):
        return sections

    with (
        patch("planning.service.compose_sections", side_effect=fake_compose),
        patch("planning.service.route_visuals", side_effect=fake_route_visuals),
    ):
        result = await PlanningService().plan(
            brief,
            model=object(),
            run_llm_fn=lambda **kwargs: SimpleNamespace(output=None),
            generation_id="trace-1",
        )

    assert len(calls) == 2
    assert "repair_instructions" in calls[1]
    assert result.template_id == "guided-concept-path"
    assert result.template_decision.chosen_id == brief.resource_type
    assert result.source_brief.subtopic == brief.subtopic


async def test_planning_service_uses_fallback_when_validation_stays_invalid() -> None:
    brief = build_brief(resource_type="quick_explainer", depth="quick")
    broken = CompositionResult(
        sections=[
            PlanningSectionPlan(
                id="section-1",
                order=1,
                role="intro",
                title="Broken",
                objective="Broken",
                selected_components=[],
                rationale="Broken",
            )
        ],
        lesson_rationale="Broken",
        warning=None,
    )

    async def fake_route_visuals(brief, directives, template, sections, **kwargs):
        return sections

    with (
        patch("planning.service.compose_sections", side_effect=[broken, broken]),
        patch("planning.service.route_visuals", side_effect=fake_route_visuals),
    ):
        result = await PlanningService().plan(
            brief,
            model=object(),
            run_llm_fn=lambda **kwargs: SimpleNamespace(output=None),
            generation_id="trace-2",
        )

    assert result.warning is not None
    assert result.template_id == "guided-concept-path"
    assert result.sections
