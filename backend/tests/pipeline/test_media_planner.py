from __future__ import annotations

from pipeline.media.planner.media_planner import media_planner
from pipeline.media.types import MediaPlan, VisualFrame, VisualSlot
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import PipelineRequest, SectionPlan, SectionVisualPolicy
from pipeline.types.section_content import (
    ComparisonColumn,
    ComparisonGridContent,
    ComparisonRow,
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    ProcessContent,
    ProcessStepItem,
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


def _contract(*, required: list[str] | None = None, optional: list[str] | None = None) -> TemplateContractSummary:
    return TemplateContractSummary(
        id="guided-concept-path",
        name="Guided Concept Path",
        family="guided-concept",
        intent="introduce-concept",
        tagline="test",
        lesson_flow=["Hook", "Explain", "Practice"],
        required_components=required or [
            "section-header",
            "hook-hero",
            "explanation-block",
            "practice-stack",
            "what-next-bridge",
        ],
        optional_components=optional or ["diagram-block", "simulation-block"],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
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


def _request() -> PipelineRequest:
    return PipelineRequest(
        subject="Mathematics",
        context="Teach rates of change",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        generation_id="gen-test",
    )


def _section(
    *,
    sid: str = "s-01",
    comparison_grid: ComparisonGridContent | None = None,
    process: ProcessContent | None = None,
) -> SectionContent:
    return SectionContent(
        section_id=sid,
        template_id="guided-concept-path",
        header=SectionHeaderContent(title="Rates of change", subject="Mathematics", grade_band="secondary"),
        hook=HookHeroContent(headline="Why this matters", body="A concise hook.", anchor="rates"),
        explanation=ExplanationContent(
            body="Rates of change help explain how one quantity responds to another.",
            emphasis=["rate of change", "input and output", "slope"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="What changes?",
                    hints=[PracticeHint(level=1, text="Compare the values.")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next we connect this to graphs.", next="Graphs"),
        comparison_grid=comparison_grid,
        process=process,
    )


def test_media_types_support_caption_and_frame_retry_contract() -> None:
    frame = VisualFrame(
        slot_id="diagram",
        index=0,
        generation_goal="Show the core concept clearly.",
        must_include=["slope"],
        avoid=["text overlays"],
        output_placeholders={"svg_content": None},
    )
    slot = VisualSlot(
        slot_id="diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        fallback_render="image",
        pedagogical_intent="Explain structure.",
        caption="A final caption owned by the slot.",
        frames=[frame],
    )
    plan = MediaPlan(section_id="s-01", slots=[slot])

    assert plan.slots[0].caption == "A final caption owned by the slot."
    assert plan.slots[0].frames[0].status == "planned"


def test_state_accepts_media_plans_without_breaking_parsing() -> None:
    media_plan = MediaPlan(section_id="s-01")
    state = TextbookPipelineState(
        request=_request(),
        contract=_contract(),
        media_plans={"s-01": media_plan},
    )

    assert state.media_plans["s-01"].section_id == "s-01"


def test_media_planner_builds_single_diagram_plan() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Rates of change",
            position=1,
            focus="Make the concept visible.",
            needs_diagram=True,
            visual_policy=SectionVisualPolicy(required=True, mode="svg"),
        ),
        section_content=_section(),
        template_contract=_contract(),
        style_context=_style_context(),
    )

    assert [slot.slot_type.value for slot in plan.slots] == ["diagram", "simulation"]
    assert plan.slots[0].frames[0].must_include


def test_media_planner_defaults_base_diagram_slot_to_image_render() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Rates of change",
            position=1,
            focus="Make the concept visible.",
            needs_diagram=True,
        ),
        section_content=_section(),
        template_contract=_contract(),
        style_context=_style_context(),
    )

    diagram_slot = next(slot for slot in plan.slots if slot.slot_type.value == "diagram")
    assert diagram_slot.preferred_render.value == "image"
    assert diagram_slot.fallback_render is not None
    assert diagram_slot.fallback_render.value == "svg"


def test_media_planner_builds_compare_plan_with_seeded_labels() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Compare states",
            position=1,
            focus="Show differences clearly.",
            needs_diagram=True,
            required_components=["diagram-compare"],
            role="compare",
            visual_policy=SectionVisualPolicy(required=True, intent="compare_variants"),
        ),
        section_content=_section(
            comparison_grid=ComparisonGridContent(
                title="Compare",
                columns=[
                    ComparisonColumn(id="before", title="Before push", summary="Unbalanced"),
                    ComparisonColumn(id="after", title="After push", summary="Balanced"),
                ],
                rows=[ComparisonRow(criterion="Net force", values=["Non-zero", "Zero"])],
            )
        ),
        template_contract=_contract(optional=["diagram-compare", "simulation-block"]),
        style_context=_style_context(),
    )

    compare_slot = next(slot for slot in plan.slots if slot.slot_type.value == "diagram_compare")
    assert [frame.label for frame in compare_slot.frames] == ["Before push", "After push"]


def test_media_planner_builds_series_plan_from_process_steps() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Three-step flow",
            position=1,
            focus="Teach the sequence.",
            needs_diagram=True,
            required_components=["diagram-series"],
            visual_policy=SectionVisualPolicy(required=True, intent="demonstrate_process"),
        ),
        section_content=_section(
            process=ProcessContent(
                title="Sequence",
                steps=[
                    ProcessStepItem(number=1, action="Start", detail="Begin."),
                    ProcessStepItem(number=2, action="Transform", detail="Change it."),
                    ProcessStepItem(number=3, action="Conclude", detail="Finish."),
                ],
            )
        ),
        template_contract=_contract(optional=["diagram-series", "simulation-block"]),
        style_context=_style_context(),
    )

    series_slot = next(slot for slot in plan.slots if slot.slot_type.value == "diagram_series")
    assert [frame.label for frame in series_slot.frames] == ["Start", "Transform", "Conclude"]


def test_media_planner_represents_simulation_separately() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Interactive view",
            position=1,
            focus="Let learners manipulate the idea.",
            interaction_policy="required",
            visual_policy=SectionVisualPolicy(simulation_intent="Explore the changing slope."),
        ),
        section_content=_section(),
        template_contract=_contract(optional=["simulation-block"]),
        style_context=_style_context(),
    )

    simulation_slot = next(slot for slot in plan.slots if slot.slot_type.value == "simulation")
    assert simulation_slot.preferred_render.value == "html_simulation"
    assert simulation_slot.simulation_intent == "Explore the changing slope."
