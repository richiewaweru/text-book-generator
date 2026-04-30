from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from planning.fallback import build_fallback_composition, build_fallback_spec
from planning.models import CompositionResult, PlanningSectionPlan, PlanValidationResult
from planning.plan_validator import validate_plan
from planning.service import (
    PlanningService,
    _enrich_planning_sections,
    _resolve_directives,
    _resolve_roles,
)
from pipeline.resources import get_resource_template
from pipeline.types.teacher_brief import TeacherBrief


def build_brief(**overrides) -> TeacherBrief:
    payload = {
        "subject": "Math",
        "topic": "Algebra",
        "subtopics": ["Solving two-step equations"],
        "grade_level": "grade_7",
        "grade_band": "adult",
        "class_profile": {
            "reading_level": "on_grade",
            "language_support": "none",
            "confidence": "mixed",
            "prior_knowledge": "some_background",
            "pacing": "normal",
            "learning_preferences": ["visual"],
        },
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


def test_resolve_directives_uses_class_profile_signals() -> None:
    directives = _resolve_directives(
        build_brief(
            class_profile={
                "reading_level": "below_grade",
                "language_support": "many_ell",
                "confidence": "low",
                "prior_knowledge": "new_topic",
                "pacing": "short_chunks",
                "learning_preferences": ["step_by_step"],
            },
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


def test_validate_plan_rejects_hallucinated_components() -> None:
    brief = build_brief()
    template = get_resource_template(brief.resource_type)
    invalid_sections = [
        PlanningSectionPlan(
            id="section-1",
            order=1,
            role="practice",
            title="Bad practice",
            objective="Practice.",
            selected_components=["vocabulary-matcher"],
            rationale="Hallucinated component.",
        )
    ]

    result = validate_plan(
        brief=brief,
        template=template,
        sections=invalid_sections,
        roles=["intro", "practice", "summary"],
    )

    assert result.is_valid is False
    assert any("unknown components" in issue.message for issue in result.issues)


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
    assert result.source_brief.subtopics == brief.subtopics


async def test_planning_service_enriches_before_visual_routing() -> None:
    brief = build_brief()
    composition = CompositionResult(
        sections=build_sections(),
        lesson_rationale="A short worksheet that introduces the method and checks it.",
        warning=None,
    )
    stage_order: list[str] = []

    async def fake_compose(*args, **kwargs):
        _ = (args, kwargs)
        stage_order.append("compose")
        return composition

    async def fake_enrich(*, brief, sections, model, run_llm_fn, generation_id):
        _ = (brief, model, run_llm_fn, generation_id)
        stage_order.append("enrich")
        return [
            section.model_copy(
                update={
                    "bridges_to": "Try the method" if section.id == "section-1" else section.bridges_to,
                    "terms_to_define": ["two-step equation"] if section.id == "section-1" else [],
                }
            )
            for section in sections
        ]

    async def fake_route_visuals(brief, directives, template, sections, **kwargs):
        _ = (brief, directives, template, kwargs)
        stage_order.append("route")
        assert sections[0].bridges_to == "Try the method"
        assert sections[0].terms_to_define == ["two-step equation"]
        return sections

    with (
        patch("planning.service.compose_sections", side_effect=fake_compose),
        patch("planning.service.validate_plan", return_value=PlanValidationResult(is_valid=True, issues=[])),
        patch("planning.service._enrich_planning_sections", side_effect=fake_enrich),
        patch("planning.service.route_visuals", side_effect=fake_route_visuals),
    ):
        result = await PlanningService().plan(
            brief,
            model=object(),
            run_llm_fn=lambda **kwargs: SimpleNamespace(output=None),
            generation_id="trace-order",
        )

    assert stage_order == ["compose", "enrich", "route"]
    assert result.sections[0].bridges_to == "Try the method"
    assert result.sections[0].terms_to_define == ["two-step equation"]


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


async def test_enrich_planning_sections_returns_original_sections_when_llm_fails() -> None:
    brief = build_brief()
    sections = build_sections()

    async def failing_run_llm(**kwargs):
        _ = kwargs
        raise RuntimeError("llm unavailable")

    enriched = await _enrich_planning_sections(
        brief=brief,
        sections=sections,
        model=object(),
        run_llm_fn=failing_run_llm,
        generation_id="trace-failure",
    )

    assert enriched[0].terms_to_define == []
    assert enriched[0].bridges_from is None
    assert enriched[0].bridges_to == sections[1].objective
    assert enriched[1].bridges_from == sections[0].objective
    assert enriched[2].bridges_to is None


def test_fallback_distributes_subtopics_across_content_sections() -> None:
    brief = build_brief(
        resource_type="worksheet",
        subtopics=[
            "What is Photosynthesis?",
            "Chlorophyll",
            "Inputs and Outputs",
        ],
    )
    template = get_resource_template(brief.resource_type)

    result = build_fallback_composition(
        brief=brief,
        template=template,
        roles=["intro", "explain", "visual", "practice", "summary"],
    )

    explain_section = result.sections[1]
    visual_section = result.sections[2]
    practice_section = result.sections[3]

    assert explain_section.focus_note == "What is Photosynthesis? + Inputs and Outputs"
    assert visual_section.focus_note == "Chlorophyll"
    assert practice_section.practice_target == (
        "Confirm the learner can apply: What is Photosynthesis? + Inputs and Outputs, "
        "Chlorophyll."
    )


def test_fallback_warns_when_subtopics_are_condensed() -> None:
    brief = build_brief(
        resource_type="quick_explainer",
        subtopics=[
            "What is Photosynthesis?",
            "Chlorophyll",
            "Inputs and Outputs",
            "The Role of Sunlight and Energy",
        ],
    )
    template = get_resource_template(brief.resource_type)

    result = build_fallback_composition(
        brief=brief,
        template=template,
        roles=["intro", "explain", "visual", "summary"],
    )

    assert result.warning == (
        "Planning used a deterministic fallback. 4 subtopics were condensed into 2 "
        "content section(s). Review the structure before generating."
    )
    assert result.sections[1].title.endswith("What is Photosynthesis? + Inputs and Outputs")
    assert result.sections[2].title.endswith("Chlorophyll + The Role of Sunlight and Energy")


def test_fallback_keeps_single_subtopic_across_all_sections() -> None:
    brief = build_brief(resource_type="quick_explainer")
    template = get_resource_template(brief.resource_type)

    result = build_fallback_composition(
        brief=brief,
        template=template,
        roles=["intro", "explain", "summary"],
    )

    assert [section.focus_note for section in result.sections] == [
        "Solving two-step equations",
        "Solving two-step equations",
        "Solving two-step equations",
    ]
    assert all("Solving two-step equations" in section.title for section in result.sections)


def test_fallback_spec_sets_visual_placements_for_visual_role_sections() -> None:
    brief = build_brief(
        supports=["visuals"],
        resource_type="worksheet",
    )
    template = get_resource_template(brief.resource_type)

    spec = build_fallback_spec(
        brief=brief,
        template=template,
        roles=["intro", "visual", "summary"],
        directives=_resolve_directives(brief),
    )

    visual_sections = [section for section in spec.sections if section.role == "visual"]

    assert visual_sections
    for section in visual_sections:
        assert section.visual_placements
        assert all(placement.block == "section" for placement in section.visual_placements)


def test_fallback_spec_assigns_terms_and_bridges() -> None:
    brief = build_brief(
        supports=["visuals"],
        resource_type="worksheet",
        subtopics=["What is Photosynthesis?", "Chlorophyll", "Inputs and Outputs"],
    )
    template = get_resource_template(brief.resource_type)

    spec = build_fallback_spec(
        brief=brief,
        template=template,
        roles=["intro", "explain", "visual", "practice", "summary"],
        directives=_resolve_directives(brief),
    )

    assert spec.sections[1].terms_to_define == ["What is Photosynthesis?"]
    assert spec.sections[2].terms_to_define == ["Chlorophyll", "Inputs and Outputs"]
    assert spec.sections[3].terms_assumed == ["What is Photosynthesis?", "Chlorophyll", "Inputs and Outputs"]
    assert spec.sections[3].practice_target == (
        "Confirm the learner can apply: What is Photosynthesis?, Chlorophyll, Inputs and Outputs."
    )
    assert spec.sections[0].bridges_from is None
    assert spec.sections[0].bridges_to == spec.sections[1].focus_note
    assert spec.sections[1].bridges_from == spec.sections[0].objective
