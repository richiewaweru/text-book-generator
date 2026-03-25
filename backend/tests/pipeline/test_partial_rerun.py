from __future__ import annotations

import pytest

from pipeline.graph import fan_out_sections
from pipeline.run import _seed_initial_state
from pipeline.state import QCReport, StyleContext, TextbookPipelineState
from pipeline.types.requests import PipelineRequest, SectionPlan, SeedDocument
from pipeline.types.section_content import (
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


def _request(**overrides) -> PipelineRequest:
    defaults = dict(
        topic="Introduction to derivatives",
        subject="Mathematics",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=3,
        generation_id="gen-test",
    )
    defaults.update(overrides)
    return PipelineRequest(**defaults)


def _plan(sid: str, position: int = 1) -> SectionPlan:
    return SectionPlan(
        section_id=sid,
        title=f"Section {sid}",
        position=position,
        focus="Core idea.",
        needs_diagram=True,
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


def _section(sid: str) -> SectionContent:
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
    )


def _state_with_curriculum(
    plans: list[str],
    *,
    target_section_ids: list[str] | None = None,
) -> TextbookPipelineState:
    request = _request(target_section_ids=target_section_ids or [])
    return TextbookPipelineState(
        request=request,
        contract=_contract(),
        curriculum_outline=[
            _plan(sid, position=i + 1) for i, sid in enumerate(plans)
        ],
        style_context=_style_context(),
    )


# ---------------------------------------------------------------------------
# fan_out_sections tests
# ---------------------------------------------------------------------------


def test_fan_out_sections_filters_to_target_ids() -> None:
    state = _state_with_curriculum(
        plans=["s-01", "s-02", "s-03"],
        target_section_ids=["s-02"],
    )
    sends = fan_out_sections(state)
    assert len(sends) == 1
    assert sends[0].arg["current_section_id"] == "s-02"


def test_fan_out_sections_runs_all_without_target_ids() -> None:
    state = _state_with_curriculum(plans=["s-01", "s-02", "s-03"])
    sends = fan_out_sections(state)
    assert len(sends) == 3
    ids = {s.arg["current_section_id"] for s in sends}
    assert ids == {"s-01", "s-02", "s-03"}


# ---------------------------------------------------------------------------
# _seed_initial_state tests
# ---------------------------------------------------------------------------


def test_seed_initial_state_pre_populates_non_targeted_sections() -> None:
    seed = SeedDocument(
        sections=[_section("s-01"), _section("s-02")],
    )
    command = _request(
        seed_document=seed,
        target_section_ids=["s-02"],
    )
    plans = [_plan("s-01", 1), _plan("s-02", 2)]
    initial = TextbookPipelineState(
        request=command,
        contract=_contract(),
        curriculum_outline=plans,
        style_context=_style_context(),
    )
    seeded = _seed_initial_state(initial=initial, command=command)

    # s-01 is not targeted → pre-seeded into assembled_sections
    assert "s-01" in seeded.assembled_sections
    assert seeded.assembled_sections["s-01"].section_id == "s-01"
    # s-02 is targeted → must NOT be pre-seeded
    assert "s-02" not in seeded.assembled_sections


def test_seed_initial_state_does_not_seed_targeted_section() -> None:
    seed = SeedDocument(sections=[_section("s-01")])
    command = _request(
        seed_document=seed,
        target_section_ids=["s-01"],
    )
    plans = [_plan("s-01", 1)]
    initial = TextbookPipelineState(
        request=command,
        contract=_contract(),
        curriculum_outline=plans,
        style_context=_style_context(),
    )
    seeded = _seed_initial_state(initial=initial, command=command)

    assert "s-01" not in seeded.assembled_sections
    assert "s-01" not in seeded.generated_sections
