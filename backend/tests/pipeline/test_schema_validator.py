from __future__ import annotations

import pytest

from pipeline.contracts import get_contract, get_section_content_schema
from pipeline.nodes import schema_validator as schema_validator_module
from pipeline.nodes.schema_validator import schema_validator
from pipeline.state import TextbookPipelineState
from pipeline.types.requests import PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    SummaryBlockContent,
    SummaryItem,
    WhatNextContent,
)


def _request() -> PipelineRequest:
    return PipelineRequest(
        context="Topic",
        subject="Math",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=1,
        generation_id="gen-schema",
    )


def _section(with_summary: bool = False) -> SectionContent:
    section = SectionContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(title="Intro", subject="Math", grade_band="secondary"),
        hook=HookHeroContent(headline="Why", body="Because", anchor="anchor"),
        explanation=ExplanationContent(body="Body", emphasis=["Body"]),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="1+1?",
                    hints=[PracticeHint(level=1, text="Count")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next topic", next="Next"),
    )
    if with_summary:
        return section.model_copy(
            update={
                "summary": SummaryBlockContent(
                    items=[SummaryItem(text="Point one"), SummaryItem(text="Point two")]
                )
            }
        )
    return section


def _state(section: SectionContent, required_components: list[str]) -> TextbookPipelineState:
    plan = SectionPlan(
        section_id=section.section_id,
        title="Section",
        position=1,
        focus="Focus",
        required_components=required_components,
        optional_components=[],
    )
    return TextbookPipelineState(
        request=_request(),
        contract=get_contract("guided-concept-path"),
        current_section_id=section.section_id,
        current_section_plan=plan,
        generated_sections={section.section_id: section},
    )


@pytest.mark.asyncio
async def test_schema_validator_fails_when_required_summary_missing() -> None:
    state = _state(_section(with_summary=False), required_components=["summary-block"])
    result = await schema_validator(state)
    assert result["errors"][0].node == "schema_validator"
    assert "summary" in result["errors"][0].message


@pytest.mark.asyncio
async def test_schema_validator_allows_missing_external_diagram_before_media() -> None:
    state = _state(_section(with_summary=False), required_components=["diagram-block"])
    result = await schema_validator(state)
    assert "errors" not in result
    assert result["completed_nodes"] == ["schema_validator"]


def test_schema_validator_rejects_invented_fields_when_additional_properties_forbidden() -> None:
    schema = get_section_content_schema()
    failures = schema_validator_module._schema_failures(
        {
            "section_id": "s-01",
            "template_id": "guided-concept-path",
            "header": {"title": "t", "subject": "Math", "grade_band": "secondary"},
            "hook": {"headline": "h", "body": "b", "anchor": "a"},
            "explanation": {"body": "b", "emphasis": ["b"]},
            "practice": {"problems": []},
            "what_next": {"body": "n", "next": "x"},
            "invented_field": {"nope": True},
        },
        schema,
    )
    assert any(failure["type"] == "additionalProperties" for failure in failures)


@pytest.mark.asyncio
async def test_schema_validator_passes_valid_section() -> None:
    state = _state(_section(with_summary=True), required_components=["summary-block"])
    result = await schema_validator(state)
    assert "errors" not in result
    assert result["completed_nodes"] == ["schema_validator"]
