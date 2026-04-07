from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from pipeline.nodes.composition_planner import (
    CompositionDecision,
    DiagramDecision,
    InteractionDecision,
    _to_composition_plan,
    composition_planner,
    pick_interaction_type,
)
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import GenerationMode, PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    ComparisonColumn,
    ComparisonGridContent,
    ComparisonRow,
    DiagramCompareContent,
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


def _section(
    sid: str = "s-01",
    *,
    diagram_compare: DiagramCompareContent | None = None,
    comparison_grid: ComparisonGridContent | None = None,
) -> SectionContent:
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
        diagram_compare=diagram_compare,
        comparison_grid=comparison_grid,
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
async def test_interaction_disabled_when_request_mode_is_draft() -> None:
    state = _state(
        request=_request(mode=GenerationMode.DRAFT),
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


# ---------------------------------------------------------------------------
# LLM-powered composition tests
# ---------------------------------------------------------------------------


def _mock_llm_decision(
    *,
    diagram_enabled: bool = False,
    interactions: list[InteractionDecision] | None = None,
) -> CompositionDecision:
    """Helper to build a CompositionDecision for mocking."""
    return CompositionDecision(
        diagram=DiagramDecision(
            enabled=diagram_enabled,
            reasoning="LLM decided this",
            diagram_type="concept_map" if diagram_enabled else None,
            key_concepts=["derivative", "slope"],
        ),
        interactions=interactions or [],
        reasoning="LLM overall reasoning",
        confidence="high",
    )


def test_to_composition_plan_enforces_guard_rails() -> None:
    """Guard-rail overrides force-disable even if LLM says enabled."""
    decision = _mock_llm_decision(
        diagram_enabled=True,
        interactions=[
            InteractionDecision(
                enabled=True,
                reasoning="LLM wants this",
                interaction_type="graph_slider",
                manipulable_element="slope",
                response_element="line",
                pedagogical_payoff="see slope effect",
            )
        ],
    )

    plan = _to_composition_plan(
        decision,
        section=_section("s-01"),
        diagram_allowed=False,
        interaction_allowed=False,
    )
    assert plan.diagram.enabled is False
    assert plan.interaction.enabled is False
    assert all(not i.enabled for i in plan.interactions)


def test_to_composition_plan_populates_interactions_list() -> None:
    """LLM decision with multiple interactions is correctly converted."""
    decision = _mock_llm_decision(
        interactions=[
            InteractionDecision(
                enabled=True,
                reasoning="Parameter exploration",
                interaction_type="graph_slider",
                manipulable_element="slope m",
                response_element="line steepness",
                pedagogical_payoff="see m controls steepness",
            ),
            InteractionDecision(
                enabled=True,
                reasoning="Step reveal",
                interaction_type="equation_reveal",
                manipulable_element="steps",
                response_element="equation",
                pedagogical_payoff="see derivation process",
            ),
        ],
    )

    plan = _to_composition_plan(
        decision,
        section=_section("s-01"),
        diagram_allowed=True,
        interaction_allowed=True,
    )
    assert len(plan.interactions) == 2
    assert plan.interactions[0].interaction_type == "graph_slider"
    assert plan.interactions[1].interaction_type == "equation_reveal"
    # Singular field mirrors first enabled interaction
    assert plan.interaction.enabled is True
    assert plan.interaction.interaction_type == "graph_slider"


def test_to_composition_plan_populates_compare_labels_from_comparison_grid() -> None:
    decision = _mock_llm_decision(diagram_enabled=True)
    plan = _to_composition_plan(
        decision,
        section=_section(
            "s-01",
            comparison_grid=ComparisonGridContent(
                title="Compare",
                columns=[
                    ComparisonColumn(id="before", title="Before state", summary="Earlier"),
                    ComparisonColumn(id="after", title="After state", summary="Later"),
                ],
                rows=[ComparisonRow(criterion="Motion", values=["Rest", "Movement"])],
            ),
        ),
        diagram_allowed=True,
        interaction_allowed=False,
    )

    assert plan.diagram.compare_before_label == "Before state"
    assert plan.diagram.compare_after_label == "After state"


def test_to_composition_plan_falls_back_to_existing_compare_labels_or_defaults() -> None:
    decision = _mock_llm_decision(diagram_enabled=True)
    seeded = _to_composition_plan(
        decision,
        section=_section(
            "s-01",
            diagram_compare=DiagramCompareContent(
                before_label="Natural",
                after_label="Driven",
                caption="Caption",
                alt_text="Alt text",
            ),
        ),
        diagram_allowed=True,
        interaction_allowed=False,
    )
    defaulted = _to_composition_plan(
        decision,
        section=_section("s-01"),
        diagram_allowed=True,
        interaction_allowed=False,
    )

    assert seeded.diagram.compare_before_label == "Natural"
    assert seeded.diagram.compare_after_label == "Driven"
    assert defaulted.diagram.compare_before_label is None
    assert defaulted.diagram.compare_after_label is None


_TEST_MODEL_OVERRIDES = {"fast": TestModel()}


async def _run_with_mock_llm(state, mock_result):
    """Run composition_planner with mocked LLM, returning the mock decision."""
    with patch("pipeline.nodes.composition_planner.run_llm", new_callable=AsyncMock, return_value=mock_result):
        return await composition_planner(state, model_overrides=_TEST_MODEL_OVERRIDES)


@pytest.mark.asyncio
async def test_llm_success_uses_llm_decision() -> None:
    """When LLM succeeds, the plan uses LLM output (not heuristic)."""
    mock_result = MagicMock()
    mock_result.output = _mock_llm_decision(
        diagram_enabled=True,
        interactions=[
            InteractionDecision(
                enabled=True,
                reasoning="LLM chose this",
                interaction_type="equation_reveal",
                manipulable_element="steps",
                response_element="equation",
                pedagogical_payoff="see process",
            )
        ],
    )

    state = _state(generated_sections={"s-01": _section("s-01")})
    result = await _run_with_mock_llm(state, mock_result)

    plan = result["composition_plans"]["s-01"]
    assert plan.interaction.interaction_type == "equation_reveal"
    assert plan.reasoning == "LLM overall reasoning"
    assert plan.confidence == "high"


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_heuristic() -> None:
    """When LLM fails, heuristic fallback produces a valid plan."""
    state = _state(generated_sections={"s-01": _section("s-01")})

    with patch("pipeline.nodes.composition_planner.run_llm", new_callable=AsyncMock, side_effect=RuntimeError("API error")):
        result = await composition_planner(state, model_overrides=_TEST_MODEL_OVERRIDES)

    plan = result["composition_plans"]["s-01"]
    # Heuristic still produces a valid plan
    assert plan.diagram.enabled is True
    assert plan.interaction.enabled is True
    assert plan.interaction.interaction_type == "graph_slider"  # math default


@pytest.mark.asyncio
async def test_interaction_usage_incremented() -> None:
    """interaction_usage tracking is updated from the composition plan."""
    mock_result = MagicMock()
    mock_result.output = _mock_llm_decision(
        interactions=[
            InteractionDecision(
                enabled=True,
                reasoning="test",
                interaction_type="timeline_scrubber",
                manipulable_element="time",
                response_element="events",
                pedagogical_payoff="see sequence",
            )
        ],
    )

    state = _state(
        request=_request(subject="History"),
        generated_sections={"s-01": _section("s-01")},
        interaction_usage={"graph_slider": 3},
    )

    result = await _run_with_mock_llm(state, mock_result)

    usage = result["interaction_usage"]
    assert usage["timeline_scrubber"] == 1
    assert usage["graph_slider"] == 3


@pytest.mark.asyncio
async def test_both_disabled_skips_llm_call() -> None:
    """When both diagram and interaction are disabled, no LLM call is made."""
    state = _state(
        request=_request(mode=GenerationMode.DRAFT),
        current_section_plan=_plan("s-01", needs_diagram=False),
        generated_sections={"s-01": _section("s-01")},
    )

    with patch("pipeline.nodes.composition_planner.run_llm", new_callable=AsyncMock) as mock_run:
        result = await composition_planner(state)
        mock_run.assert_not_called()

    plan = result["composition_plans"]["s-01"]
    assert plan.diagram.enabled is False
    assert plan.interaction.enabled is False
