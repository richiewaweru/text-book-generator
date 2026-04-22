from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pipeline.events import FieldRegenOutcomeEvent
from pipeline.nodes.field_regenerator import field_regenerator
from pipeline.state import RerenderRequest, TextbookPipelineState
from pipeline.types.requests import GenerationMode, PipelineRequest
from pipeline.types.section_content import (
    CalloutBlockContent,
    ExplanationContent,
    FillInBlankContent,
    FillInBlankSegment,
    HookHeroContent,
    KeyFactContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    SectionDividerContent,
    ShortAnswerContent,
    StudentTextboxContent,
    SummaryBlockContent,
    SummaryItem,
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


def _section(
    *,
    callout: CalloutBlockContent | None = None,
    summary: SummaryBlockContent | None = None,
) -> SectionContent:
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
        callout=callout,
        summary=summary,
    )


def _state(
    *,
    block_type: str = "explanation",
    section: SectionContent | None = None,
) -> TextbookPipelineState:
    section = section or _section()
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(),
        current_section_id=section.section_id,
        generated_sections={section.section_id: section},
        assembled_sections={section.section_id: section},
        rerender_requests={
            section.section_id: RerenderRequest(
                section_id=section.section_id,
                block_type=block_type,
                reason=f"{block_type} needs clearer wording",
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


def test_section_content_accepts_callout_and_summary_blocks() -> None:
    section = _section(
        callout=CalloutBlockContent(
            variant="remember",
            heading="Key reminder",
            body="Slope compares rise to run.",
        ),
        summary=SummaryBlockContent(
            heading="In summary",
            items=[
                SummaryItem(text="Slope measures steepness."),
                SummaryItem(text="Positive slopes rise to the right."),
            ],
            closing="You can now compare lines with confidence.",
        ),
    )

    assert section.callout is not None
    assert section.callout.variant == "remember"
    assert section.summary is not None
    assert len(section.summary.items) == 2


def test_section_content_accepts_new_enrichment_blocks() -> None:
    section = _section().model_copy(
        update={
            "student_textbox": StudentTextboxContent(prompt="Explain why the slope is positive."),
            "short_answer": ShortAnswerContent(question="Define gradient.", marks=2),
            "fill_in_blank": FillInBlankContent(
                instruction="Complete the sentence.",
                segments=[
                    FillInBlankSegment(text="Gradient is", is_blank=False),
                    FillInBlankSegment(text="", is_blank=True, answer="rise over run"),
                ],
                word_bank=["rise over run"],
            ),
            "key_fact": KeyFactContent(fact="A positive gradient rises to the right."),
            "divider": SectionDividerContent(label="Practice checkpoint"),
        }
    )

    assert section.student_textbox is not None
    assert section.short_answer is not None
    assert section.fill_in_blank is not None
    assert section.key_fact is not None
    assert section.divider is not None


@pytest.mark.parametrize(
    ("field_name", "payload"),
    [
        (
            "callout",
            {
                "variant": "tip",
                "heading": "Exam tip",
                "body": "Check the sign of the slope before you compare steepness.",
            },
        ),
        (
            "summary",
            {
                "heading": "In summary",
                "items": [
                    {"text": "Slope is rise over run."},
                    {"text": "The sign tells you direction."},
                ],
                "closing": "Next we connect this to straight-line equations.",
            },
        ),
        (
            "student_textbox",
            {
                "prompt": "Write one sentence explaining what slope measures.",
                "lines": 4,
                "label": "Your response",
            },
        ),
        (
            "short_answer",
            {
                "question": "What does a negative slope tell you?",
                "marks": 2,
                "lines": 3,
                "mark_scheme": "States the line falls from left to right.",
            },
        ),
        (
            "fill_in_blank",
            {
                "instruction": "Complete the definition.",
                "segments": [
                    {"text": "Slope is", "is_blank": False},
                    {"text": "", "is_blank": True, "answer": "rise over run"},
                ],
                "word_bank": ["rise over run"],
            },
        ),
        (
            "key_fact",
            {
                "fact": "Slope compares vertical and horizontal change.",
                "context": "This helps compare steepness quickly.",
            },
        ),
        (
            "divider",
            {
                "label": "Practice checkpoint",
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_field_regenerator_supports_extended_retryable_fields(
    monkeypatch: pytest.MonkeyPatch,
    field_name: str,
    payload: dict,
) -> None:
    state = _state(block_type=field_name)
    _capture_events(monkeypatch)
    _stub_agent_dependencies(monkeypatch)

    async def _run_llm(**kwargs):
        _ = kwargs
        return SimpleNamespace(output=json.dumps(payload))

    monkeypatch.setattr("pipeline.nodes.field_regenerator.run_llm", _run_llm)

    result = await field_regenerator(state)
    updated = result["generated_sections"]["s-01"]

    if field_name == "callout":
        assert updated.callout is not None
        assert updated.callout.body == payload["body"]
    elif field_name == "summary":
        assert updated.summary is not None
        assert updated.summary.items[0].text == payload["items"][0]["text"]
    elif field_name == "student_textbox":
        assert updated.student_textbox is not None
        assert updated.student_textbox.prompt == payload["prompt"]
    elif field_name == "short_answer":
        assert updated.short_answer is not None
        assert updated.short_answer.question == payload["question"]
    elif field_name == "fill_in_blank":
        assert updated.fill_in_blank is not None
        assert updated.fill_in_blank.segments[1].answer == "rise over run"
    elif field_name == "key_fact":
        assert updated.key_fact is not None
        assert updated.key_fact.fact == payload["fact"]
    else:
        assert updated.divider is not None
        assert updated.divider.label == payload["label"]
