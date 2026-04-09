from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pipeline.events import FieldRegenOutcomeEvent
from pipeline.nodes.field_regenerator import field_regenerator
from pipeline.state import RerenderRequest, TextbookPipelineState
from pipeline.types.requests import GenerationMode, PipelineRequest
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


def _contract() -> TemplateContractSummary:
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
        optional_components=[],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
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
        generation_id="gen-field-regen-test",
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


def _state() -> TextbookPipelineState:
    section = _section()
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(),
        current_section_id=section.section_id,
        generated_sections={section.section_id: section},
        assembled_sections={section.section_id: section},
        rerender_requests={
            section.section_id: RerenderRequest(
                section_id=section.section_id,
                block_type="explanation",
                reason="Explanation needs clearer wording",
            )
        },
    )


def _capture_events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []

    def _publish(generation_id: str, event: object) -> None:
        events.append((generation_id, event))

    monkeypatch.setattr(
        "pipeline.nodes.field_regenerator.core_events.event_bus.publish",
        _publish,
    )
    return events


def _stub_agent_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pipeline.nodes.field_regenerator.Agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        "pipeline.nodes.field_regenerator.get_node_text_model",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        "pipeline.nodes.field_regenerator.retry_policy_for_node",
        lambda *args, **kwargs: object(),
    )


@pytest.mark.asyncio
async def test_field_regenerator_emits_success_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    events = _capture_events(monkeypatch)
    _stub_agent_dependencies(monkeypatch)

    async def _run_llm(**kwargs):
        _ = kwargs
        return SimpleNamespace(
            output=json.dumps(
                {
                    "body": "Regenerated explanation",
                    "emphasis": ["new key point"],
                }
            )
        )

    monkeypatch.setattr("pipeline.nodes.field_regenerator.run_llm", _run_llm)

    result = await field_regenerator(state)

    updated = result["generated_sections"]["s-01"]
    assert updated.explanation.body == "Regenerated explanation"
    assert result["assembled_sections"]["s-01"].explanation.body == "Regenerated explanation"
    assert len(events) == 1
    generation_id, event = events[0]
    assert generation_id == "gen-field-regen-test"
    assert isinstance(event, FieldRegenOutcomeEvent)
    assert event.field_name == "explanation"
    assert event.outcome == "success"
    assert event.error_message is None


@pytest.mark.asyncio
async def test_field_regenerator_emits_failure_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    events = _capture_events(monkeypatch)
    _stub_agent_dependencies(monkeypatch)

    async def _run_llm(**kwargs):
        _ = kwargs
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("pipeline.nodes.field_regenerator.run_llm", _run_llm)

    result = await field_regenerator(state)

    assert result["completed_nodes"] == ["field_regenerator"]
    assert "Field regeneration failed: model unavailable" == result["errors"][0].message
    assert len(events) == 1
    generation_id, event = events[0]
    assert generation_id == "gen-field-regen-test"
    assert isinstance(event, FieldRegenOutcomeEvent)
    assert event.field_name == "explanation"
    assert event.outcome == "failed"
    assert event.error_message == "Field regeneration failed: model unavailable"
