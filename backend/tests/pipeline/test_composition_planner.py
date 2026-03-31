from __future__ import annotations

import pytest

from pipeline.nodes.composition_planner import composition_planner, pick_interaction_type
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeProblem,
    PracticeHint,
    SectionContent,
    SectionHeaderContent,
    WhatNextContent,
)
from pipeline.types.template_contract import GenerationGuidance, TemplateContractSummary


def _guidance() -> GenerationGuidance:
    return GenerationGuidance(
        tone="clear",
        pacing="steady",
        chunking="medium",
        emphasis="explanation first",
        avoid=["long prose"],
    )


def _contract(**overrides) -> TemplateContractSummary:
    defaults = dict(
        id="guided-concept-path",
        name="Guided Concept Path",
        family="guided-concept",
        intent="introduce-concept",
        tagline="test",
        lesson_flow=["Hook", "Explain", "Practice"],
        required_components=[
            "section-header",
            "hook-hero",
            "explanation-block",
            "practice-stack",
            "what-next-bridge",
        ],
        optional_components=["definition-card", "diagram-block", "simulation-block"],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
    )
    defaults.update(overrides)
    return TemplateContractSummary(**defaults)


def _request(**overrides) -> PipelineRequest:
    defaults = dict(
        topic="Introduction to derivatives",
        subject="Mathematics",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=1,
        generation_id="gen-test",
    )
    defaults.update(overrides)
    return PipelineRequest(**defaults)


def _plan(sid: str = "s-01", *, needs_diagram: bool = True) -> SectionPlan:
    return SectionPlan(
        section_id=sid,
        title=f"Section {sid}",
        position=1,
        focus="Teach the core idea clearly.",
        needs_diagram=needs_diagram,
    )


def _style_context() -> StyleContext:
    return StyleContext(
        preset_id="blue-classroom",
        palette="navy, sky, parchment",
        surface_style="crisp",
        density="standard",
        typography="standard",
        template_id="guided-concept-path",
        template_family="guided-concept",
        interaction_level="medium",
        grade_band="secondary",
        learner_fit="general",
    )


def _section(sid: str = "s-01") -> SectionContent:
    return SectionContent(
        section_id=sid,
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title=f"Section {sid}",
            subject="Mathematics",
            grade_band="secondary",
        ),
        hook=HookHeroContent(
            headline="Why this matters",
            body="A compelling hook body",
            anchor="derivatives",
        ),
        explanation=ExplanationContent(
            body="The explanation of the concept",
            emphasis=["key point 1", "key point 2"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="What is 2+2?",
                    hints=[PracticeHint(level=1, text="Think about it")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next we cover integrals", next="Integrals"),
    )


def _state(**overrides) -> TextbookPipelineState:
    defaults = dict(
        request=_request(),
        contract=_contract(),
        current_section_id="s-01",
        current_section_plan=_plan("s-01"),
        curriculum_outline=[_plan("s-01")],
        style_context=_style_context(),
    )
    defaults.update(overrides)
    return TextbookPipelineState(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skips_when_section_not_generated() -> None:
    state = _state()  # generated_sections is empty
    result = await composition_planner(state)
    assert "composition_plans" not in result
    assert result["completed_nodes"] == ["composition_planner"]


@pytest.mark.asyncio
async def test_diagram_enabled_when_plan_and_contract_support() -> None:
    state = _state(
        generated_sections={"s-01": _section("s-01")},
        current_section_plan=_plan("s-01", needs_diagram=True),
    )
    result = await composition_planner(state)
    plan = result["composition_plans"]["s-01"]
    assert plan.diagram.enabled is True
    assert plan.diagram.diagram_type is not None


@pytest.mark.asyncio
async def test_diagram_disabled_when_plan_says_no() -> None:
    state = _state(
        generated_sections={"s-01": _section("s-01")},
        current_section_plan=_plan("s-01", needs_diagram=False),
    )
    result = await composition_planner(state)
    plan = result["composition_plans"]["s-01"]
    assert plan.diagram.enabled is False
    assert plan.diagram.diagram_type is None


@pytest.mark.asyncio
async def test_interaction_disabled_when_plan_policy_disables_it() -> None:
    state = _state(
        current_section_plan=_plan("s-01").model_copy(update={"interaction_policy": "disabled"}),
        generated_sections={"s-01": _section("s-01")},
    )
    result = await composition_planner(state)
    plan = result["composition_plans"]["s-01"]
    assert plan.interaction.enabled is False
    assert plan.interaction.interaction_type is None


@pytest.mark.asyncio
async def test_interaction_type_history_subject_gives_timeline_scrubber() -> None:
    state = _state(
        request=_request(subject="History"),
        generated_sections={"s-01": _section("s-01")},
    )
    result = await composition_planner(state)
    plan = result["composition_plans"]["s-01"]
    assert plan.interaction.enabled is True
    assert plan.interaction.interaction_type == "timeline_scrubber"


def test_pick_interaction_type_math_defaults_to_graph_slider() -> None:
    state = _state(request=_request(subject="Mathematics"))
    section = _section("s-01")
    assert pick_interaction_type(state, section) == "graph_slider"


def test_pick_interaction_type_probability_gives_probability_tree() -> None:
    state = _state(request=_request(subject="Probability and Statistics"))
    section = _section("s-01")
    assert pick_interaction_type(state, section) == "probability_tree"
