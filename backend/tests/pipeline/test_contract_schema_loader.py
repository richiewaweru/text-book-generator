from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.contracts import (
    clear_cache,
    get_component_generation_hint,
    get_field_schema,
    get_section_field_for_component,
    list_template_ids,
)
from pipeline.types.section_content import (
    DiagramContent,
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    WorkedExampleContent,
    WhatNextContent,
)


def _valid_section() -> SectionContent:
    return SectionContent(
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


def test_contract_loader_excludes_schema_file_from_template_ids() -> None:
    clear_cache()
    template_ids = list_template_ids()
    assert "section-content-schema" not in template_ids


def test_contract_helpers_resolve_generation_hint_field_map_and_schema() -> None:
    clear_cache()
    assert get_component_generation_hint("summary-block")
    assert get_section_field_for_component("summary-block") == "summary"
    summary_schema = get_field_schema("summary")
    assert isinstance(summary_schema, dict)
    assert summary_schema.get("type") == "object"
    assert "properties" in summary_schema


def test_generated_section_content_accepts_and_serializes_lectio_shape() -> None:
    section = _valid_section()
    payload = section.model_dump(exclude_none=True)
    assert payload["what_next"]["next"] == "Next"
    assert "what_next" in payload


def test_generated_section_content_rejects_invalid_field_types() -> None:
    with pytest.raises(ValidationError):
        SectionContent(
            section_id="s-01",
            template_id="guided-concept-path",
            header="not-an-object",  # type: ignore[arg-type]
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


def test_synced_lectio_contract_keeps_inline_diagram_fields() -> None:
    lectio_types = Path("frontend/node_modules/lectio/dist/schema/types.d.ts").read_text(
        encoding="utf-8"
    )
    assert "export interface PracticeProblem {\n    diagram?: DiagramContent;" in lectio_types
    assert "export interface WorkedExampleContent {\n    diagram?: DiagramContent;" in lectio_types

    practice_problem = PracticeProblem.model_validate(
        {
            "difficulty": "warm",
            "question": "Read the diagram.",
            "hints": [{"level": 1, "text": "Follow the arrows."}],
            "diagram": {
                "caption": "A compact support diagram.",
                "alt_text": "Compact support diagram.",
                "image_url": "http://example.test/practice.png",
            },
        }
    )
    worked_example = WorkedExampleContent.model_validate(
        {
            "title": "Worked example",
            "setup": "Set up the comparison.",
            "steps": [{"label": "Step 1", "content": "Inspect the graphic."}],
            "conclusion": "Use the visual evidence.",
            "diagram": {
                "caption": "A compact worked-example diagram.",
                "alt_text": "Compact worked-example diagram.",
                "image_url": "http://example.test/worked.png",
            },
        }
    )

    assert isinstance(practice_problem.diagram, DiagramContent)
    assert isinstance(worked_example.diagram, DiagramContent)
