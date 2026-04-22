from __future__ import annotations

from pipeline.types.content_phases import (
    CoreContent,
    EnrichmentPhaseContent,
    PracticePhaseContent,
)
from pipeline.types.section_content import (
    ExplanationContent,
    FillInBlankContent,
    FillInBlankSegment,
    HookHeroContent,
    KeyFactContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionHeaderContent,
    SectionDividerContent,
    ShortAnswerContent,
    StudentTextboxContent,
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
    assert enrichment.student_textbox is None
    assert enrichment.short_answer is None
    assert enrichment.fill_in_blank is None
    assert enrichment.divider is None
    assert enrichment.key_fact is None


def test_enrichment_phase_content_accepts_new_lectio_enrichment_models() -> None:
    enrichment = EnrichmentPhaseContent(
        student_textbox=StudentTextboxContent(prompt="Explain your reasoning."),
        short_answer=ShortAnswerContent(question="What is slope?", marks=2),
        fill_in_blank=FillInBlankContent(
            instruction="Complete the definition.",
            segments=[
                FillInBlankSegment(text="Slope is", is_blank=False),
                FillInBlankSegment(text="", is_blank=True, answer="rise over run"),
            ],
        ),
        divider=SectionDividerContent(label="Practice checkpoint"),
        key_fact=KeyFactContent(fact="Slope compares vertical change to horizontal change."),
    )

    assert enrichment.student_textbox is not None
    assert enrichment.short_answer is not None
    assert enrichment.fill_in_blank is not None
    assert enrichment.divider is not None
    assert enrichment.key_fact is not None
