from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.events import (
    InteractionOutcomeEvent,
    MediaFrameReadyEvent,
    MediaFrameStartedEvent,
    MediaSlotReadyEvent,
    SimulationTypeSelectedEvent,
)
from pipeline.media.types import MediaPlan, VisualFrame, VisualSlot
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
        media_plans=(
            {
                section.section_id: MediaPlan(
                    section_id=section.section_id,
                    slots=[
                        VisualSlot(
                            slot_id="simulation",
                            slot_type="simulation",
                            required=interaction_policy == "required",
                            preferred_render="html_simulation",
                            fallback_render="svg",
                            pedagogical_intent="Let learners manipulate the idea.",
                            caption=f"Interactive exploration for {section.header.title}.",
                            frames=[
                                VisualFrame(
                                    slot_id="simulation",
                                    index=0,
                                    label=section.header.title,
                                    generation_goal=f"Represent an interactive view for {section.header.title}.",
                                    must_include=["rate of change"],
                                )
                            ],
                            simulation_intent="Explore how the graph changes.",
                            simulation_type="graph_slider",
                            simulation_goal="Explore how the graph changes.",
                            anchor_block="explanation",
                            print_translation="hide",
                        )
                    ],
                )
            }
            if with_slot and composition is not None
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


def _mock_simulation_llm(monkeypatch: pytest.MonkeyPatch, *, output: str) -> None:
    async def _run_llm(**kwargs):
        _ = kwargs
        return SimpleNamespace(output=output)

    monkeypatch.setattr(
        "pipeline.media.executors.simulation_generator.get_node_text_model",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr("pipeline.media.executors.simulation_generator.Agent", lambda *args, **kwargs: object())
    monkeypatch.setattr("pipeline.media.executors.simulation_generator.run_llm", _run_llm)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected_reason"),
    [
        (_state(interaction_policy="disabled", composition=_composition()), "policy_disabled"),
        (_state(interaction_level="low", composition=_composition()), "low_interaction_level"),
        (_state(with_slot=False, composition=_composition()), "no_plan"),
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
async def test_interaction_generator_emits_single_simulation_when_multiple_plans_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = _capture_events(monkeypatch)
    _mock_simulation_llm(
        monkeypatch,
        output=(
            "<!doctype html><html><body><button>Reset</button><input type=\"range\" /></body></html>\n"
            "SIMULATION_META:\n"
            "type: graph_slider\n"
            "goal: Explore how the graph changes.\n"
            "explanation: Move the slider to see the graph respond."
        ),
    )
    state = _state(composition=_composition(enabled=True, count=2))

    result = await interaction_generator(state)

    section = result["generated_sections"]["s-01"]
    assert not hasattr(section, "simulations")
    assert section.simulation is not None
    assert section.simulation.html_content is not None
    assert section.simulation.explanation is not None
    assert result["interaction_specs"]["s-01"].type == "graph_slider"
    assert result["media_slot_results"]["s-01"]["simulation"].ready is True
    assert [type(event) for _generation_id, event in events] == [
        MediaFrameStartedEvent,
        SimulationTypeSelectedEvent,
        MediaFrameReadyEvent,
        MediaSlotReadyEvent,
        InteractionOutcomeEvent,
    ]
    generation_id, event = events[-1]
    assert generation_id == "gen-interaction-test"
    assert isinstance(event, InteractionOutcomeEvent)
    assert event.outcome == "generated"
    assert event.skip_reason is None
    assert event.interaction_count == 1
