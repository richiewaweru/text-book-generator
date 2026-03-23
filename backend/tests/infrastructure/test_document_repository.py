from datetime import datetime, timezone

import pytest

from pipeline.api import PipelineDocument
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
from textbook_agent.infrastructure.repositories.file_document_repo import FileDocumentRepository


def _section(section_id: str = "s-01") -> SectionContent:
    return SectionContent(
        section_id=section_id,
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title="Limits in Motion",
            subject="Calculus",
            grade_band="secondary",
        ),
        hook=HookHeroContent(
            headline="Why a moving graph still tells a stable story",
            body="Limits let us describe what a function is approaching without requiring the final value yet.",
            anchor="limits",
        ),
        explanation=ExplanationContent(
            body="A limit studies nearby behavior.",
            emphasis=["nearby behavior"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="Describe what f(x) does near x = 2.",
                    hints=[PracticeHint(level=1, text="Look close to 2.")],
                ),
                PracticeProblem(
                    difficulty="medium",
                    question="Estimate lim x->2 of x^2.",
                    hints=[PracticeHint(level=1, text="Square numbers near 2.")],
                ),
            ]
        ),
        what_next=WhatNextContent(
            body="Next we connect limits to continuity.",
            next="Continuity",
        ),
    )


def _document(generation_id: str = "gen-doc") -> PipelineDocument:
    now = datetime.now(timezone.utc)
    return PipelineDocument(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        mode="balanced",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="running",
        section_manifest=[
            {
                "section_id": "s-01",
                "title": "Limits in Motion",
                "position": 1,
            }
        ],
        sections=[_section()],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_save_and_load_document_round_trip(tmp_path):
    repo = FileDocumentRepository(output_dir=str(tmp_path))
    document = _document()

    path = await repo.save_document(document)

    assert path.endswith("gen-doc.json")
    loaded = await repo.load_document(path)
    assert loaded.generation_id == document.generation_id
    assert loaded.sections[0].section_id == "s-01"
    assert loaded.template_id == "guided-concept-path"
    assert loaded.section_manifest[0].title == "Limits in Motion"


@pytest.mark.asyncio
async def test_load_document_raises_for_missing_path(tmp_path):
    repo = FileDocumentRepository(output_dir=str(tmp_path))

    with pytest.raises(FileNotFoundError):
        await repo.load_document(str(tmp_path / "missing.json"))
