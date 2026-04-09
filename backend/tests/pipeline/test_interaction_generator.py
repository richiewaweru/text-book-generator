from __future__ import annotations

import pytest

from pipeline.events import InteractionOutcomeEvent
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.state import TextbookPipelineState
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan
from pipeline.types.requests import GenerationMode, PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
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


def _contract(*, interaction_level: str = "medium", with_slot: bool = True) -> TemplateContractSummary:
    optional_components = ["simulation-block"] if with_slot else []
    return TemplateContractSummary(
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
        optional_components=optional_components,
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level=interaction_level,
        allowed_presets=["blue-classroom"],
    )


def _request() -> PipelineRequest:
    return PipelineRequest(
        topic="Introduction to derivatives",
        subject="Mathematics",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=1,
        mode=GenerationMode.BALANCED,
        generation_id="gen-interaction-test",
    )


def _section() -> SectionContent:
    return SectionContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title="Section s-01",
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
            emphasis=["key point 1"],
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


def _plan(*, interaction_policy: str = "allowed") -> SectionPlan:
    return SectionPlan(
        section_id="s-01",
        title="Test Section",
        position=1,
        focus="Test focus",
        interaction_policy=interaction_policy,
    )


def _composition(*, enabled: bool = True, count: int = 1) -> CompositionPlan:
    plans = [
        InteractionPlan(
            enabled=True,
            reasoning=f"Interaction {index + 1}",
            interaction_type="graph_slider",
            pedagogical_payoff=f"Goal {index + 1}",
        )
        for index in range(count)
    ]
    singular = plans[0] if enabled and count == 1 else InteractionPlan(enabled=False, reasoning="unused")
    return CompositionPlan(
        diagram=DiagramPlan(enabled=False, reasoning="no diagram"),
        interaction=singular if enabled else InteractionPlan(enabled=False, reasoning="disabled"),
        interactions=plans if enabled else [],
    )


def _state(
    *,
    interaction_policy: str = "allowed",
    interaction_level: str = "medium",
    with_slot: bool = True,
    composition: CompositionPlan | None = None,
) -> TextbookPipelineState:
    section = _section()
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(interaction_level=interaction_level, with_slot=with_slot),
        current_section_id=section.section_id,
        current_section_plan=_plan(interaction_policy=interaction_policy),
        generated_sections={section.section_id: section},
        composition_plans=(
            {section.section_id: composition}
            if composition is not None
            else {}
        ),
    )


def _capture_events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []

    def _publish(generation_id: str, event: object) -> None:
        events.append((generation_id, event))

    monkeypatch.setattr(
        "pipeline.nodes.interaction_generator.core_events.event_bus.publish",
        _publish,
    )
    return events


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_reason"),
    [
        (_state(interaction_policy="disabled", composition=_composition()), "policy_disabled"),
        (_state(interaction_level="low", composition=_composition()), "low_interaction_level"),
        (_state(with_slot=False, composition=_composition()), "no_slot"),
        (_state(composition=None), "no_plan"),
    ],
)
async def test_interaction_generator_emits_skip_reasons(
    monkeypatch: pytest.MonkeyPatch,
    state: TextbookPipelineState,
    expected_reason: str,
) -> None:
    events = _capture_events(monkeypatch)

    result = await interaction_generator(state)

    assert result == {"completed_nodes": ["interaction_generator"]}
    assert len(events) == 1
    generation_id, event = events[0]
    assert generation_id == "gen-interaction-test"
    assert isinstance(event, InteractionOutcomeEvent)
    assert event.outcome == "skipped"
    assert event.skip_reason == expected_reason
    assert event.interaction_count == 0


@pytest.mark.asyncio
async def test_interaction_generator_emits_generated_count_for_multiple_simulations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _capture_events(monkeypatch)
    state = _state(composition=_composition(enabled=True, count=2))

    result = await interaction_generator(state)

    section = result["generated_sections"]["s-01"]
    assert len(section.simulations) == 2
    assert section.simulation is not None
    assert result["interaction_specs"]["s-01"].type == "graph_slider"
    assert len(events) == 1
    generation_id, event = events[0]
    assert generation_id == "gen-interaction-test"
    assert isinstance(event, InteractionOutcomeEvent)
    assert event.outcome == "generated"
    assert event.skip_reason is None
    assert event.interaction_count == 2
