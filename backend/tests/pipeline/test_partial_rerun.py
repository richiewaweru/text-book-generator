from __future__ import annotations

from pipeline.graph import fan_out_sections
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import GenerationMode, PipelineRequest, SectionPlan
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


def _state_with_curriculum(plans: list[str]) -> TextbookPipelineState:
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(),
        curriculum_outline=[_plan(sid, position=index + 1) for index, sid in enumerate(plans)],
        style_context=_style_context(),
    )


def test_fan_out_sections_runs_all_sections() -> None:
    state = _state_with_curriculum(["s-01", "s-02", "s-03"])
    sends = fan_out_sections(state)

    assert len(sends) == 3
    ids = [send.arg["current_section_id"] for send in sends]
    assert ids == ["s-01", "s-02", "s-03"]


def test_initial_pipeline_state_does_not_preseed_any_sections() -> None:
    state = _state_with_curriculum(["s-01", "s-02"])

    assert state.generated_sections == {}
    assert state.assembled_sections == {}
    assert state.failed_sections == {}


def test_pipeline_request_uses_mode_specific_rerender_budget() -> None:
    assert _request(mode=GenerationMode.DRAFT).max_rerenders() == 1
    assert _request(mode=GenerationMode.BALANCED).max_rerenders() == 2
    assert _request(mode=GenerationMode.STRICT).max_rerenders() == 3


def test_pipeline_request_disables_interactions_in_draft_mode() -> None:
    assert _request(mode=GenerationMode.DRAFT).interactions_enabled() is False
    assert _request(mode=GenerationMode.BALANCED).interactions_enabled() is True
