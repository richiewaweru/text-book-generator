from __future__ import annotations

from pipeline.types.content_phases import (
    CoreContent,
    EnrichmentPhaseContent,
    PracticePhaseContent,
)
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionHeaderContent,
    WhatNextContent,
)


def test_core_content_uses_generated_lectio_models() -> None:
    core = CoreContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(title="Intro", subject="Math", grade_band="secondary"),
        hook=HookHeroContent(headline="Why", body="Because", anchor="anchor"),
        explanation=ExplanationContent(body="Body", emphasis=["Body"]),
    )
    assert isinstance(core.header, SectionHeaderContent)
    assert isinstance(core.hook, HookHeroContent)
    assert isinstance(core.explanation, ExplanationContent)


def test_practice_phase_content_uses_generated_lectio_models() -> None:
    practice_phase = PracticePhaseContent(
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
    assert isinstance(practice_phase.practice, PracticeContent)
    assert isinstance(practice_phase.what_next, WhatNextContent)


def test_enrichment_phase_content_uses_generated_lectio_models() -> None:
    enrichment = EnrichmentPhaseContent()
    assert enrichment.callout is None
    assert enrichment.summary is None
