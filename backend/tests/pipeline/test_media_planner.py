from __future__ import annotations

from pipeline.media.planner.media_planner import media_planner
from pipeline.media.types import MediaPlan, VisualFrame, VisualSlot
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import BlockVisualPlacement, PipelineRequest, SectionPlan, SectionVisualPolicy
from pipeline.types.section_content import (
    ComparisonColumn,
    ComparisonGridContent,
    ComparisonRow,
    DiagramSeriesContent,
    DiagramSeriesStep,
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
    WorkedExampleContent,
    WorkedStep,
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
        required_components=required
        or ["section-header", "hook-hero", "explanation-block", "practice-stack", "what-next-bridge"],
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
    practice_problems: list[PracticeProblem] | None = None,
    worked_example: WorkedExampleContent | None = None,
    diagram_series: DiagramSeriesContent | None = None,
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
            problems=practice_problems
            or [
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
        worked_example=worked_example,
        diagram_series=diagram_series,
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


def test_media_planner_requires_visual_placements_for_static_slots() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Rates of change",
            position=1,
            focus="Make the concept visible.",
            needs_diagram=True,
            interaction_policy="required",
            required_components=["diagram-block", "simulation-block"],
        ),
        section_content=_section(),
        template_contract=_contract(),
        style_context=_style_context(),
    )

    assert [slot.slot_type.value for slot in plan.slots] == ["simulation"]
    assert "visual_placements is empty" in " ".join(plan.planner_notes)


def test_media_planner_builds_single_diagram_from_explanation_placement() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Rates of change",
            position=1,
            focus="Make the concept visible.",
            visual_policy=SectionVisualPolicy(required=True, mode="svg"),
            visual_placements=[
                BlockVisualPlacement(block="explanation", slot_type="diagram", hint="Use a clear line diagram.")
            ],
        ),
        section_content=_section(),
        template_contract=_contract(),
        style_context=_style_context(),
    )

    diagram_slot = next(slot for slot in plan.slots if slot.slot_type.value == "diagram")
    assert diagram_slot.block_target == "explanation"
    assert diagram_slot.preferred_render.value == "svg"
    assert "Rates of change help explain" in (diagram_slot.content_brief or "")


def test_media_planner_builds_compare_plan_from_explanation_placement() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Compare states",
            position=1,
            focus="Show differences clearly.",
            role="compare",
            visual_policy=SectionVisualPolicy(required=True, mode="image"),
            visual_placements=[
                BlockVisualPlacement(block="explanation", slot_type="diagram_compare")
            ],
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
    assert compare_slot.preferred_render.value == "image"


def test_media_planner_deduplicates_series_labels_case_insensitively() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Three-step flow",
            position=1,
            focus="Teach the sequence.",
            visual_policy=SectionVisualPolicy(required=True, mode="image"),
            visual_placements=[
                BlockVisualPlacement(block="explanation", slot_type="diagram_series")
            ],
        ),
        section_content=_section(
            diagram_series=DiagramSeriesContent(
                title="Sequence",
                diagrams=[
                    DiagramSeriesStep(step_label="Start", caption="Start"),
                    DiagramSeriesStep(step_label="start", caption="Duplicate"),
                    DiagramSeriesStep(step_label="Transform", caption="Transform"),
                ],
            ),
            process=ProcessContent(
                title="Sequence",
                steps=[
                    ProcessStepItem(number=1, action="Start", detail="Begin."),
                    ProcessStepItem(number=2, action="Transform", detail="Change it."),
                ],
            ),
        ),
        template_contract=_contract(optional=["diagram-series", "simulation-block"]),
        style_context=_style_context(),
    )

    series_slot = next(slot for slot in plan.slots if slot.slot_type.value == "diagram_series")
    assert [frame.label for frame in series_slot.frames] == ["Start", "Transform"]


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


def test_media_planner_builds_compact_practice_slot_from_explicit_problem_indices() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Practice graphs",
            position=1,
            focus="Support a targeted practice problem.",
            visual_placements=[
                BlockVisualPlacement(
                    block="practice",
                    slot_type="diagram",
                    sizing="compact",
                    hint="Show the line and marked points.",
                    problem_indices=[1],
                )
            ],
        ),
        section_content=_section(
            practice_problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="State the definition.",
                    hints=[PracticeHint(level=1, text="Use the key term.")],
                ),
                PracticeProblem(
                    difficulty="medium",
                    question="Plot the line through (0,1) and (4,9).",
                    hints=[PracticeHint(level=1, text="Mark the two coordinates.")],
                ),
            ]
        ),
        template_contract=_contract(optional=["diagram-block"]),
        style_context=_style_context(),
    )

    slot = next(slot for slot in plan.slots if slot.block_target == "practice")
    assert slot.slot_id == "practice-1-diagram"
    assert slot.sizing == "compact"
    assert slot.problem_index == 1
    assert slot.frames[0].target_w == 600
    assert slot.frames[0].target_h == 400
    assert "Plot the line through (0,1) and (4,9)." in (slot.content_brief or "")


def test_media_planner_builds_compact_worked_example_slot() -> None:
    plan = media_planner(
        section_plan=SectionPlan(
            section_id="s-01",
            title="Worked example",
            position=1,
            focus="Support the worked example setup.",
            visual_placements=[
                BlockVisualPlacement(
                    block="worked_example",
                    slot_type="diagram",
                    sizing="compact",
                    hint="Show the triangle and labels.",
                )
            ],
        ),
        section_content=_section(
            worked_example=WorkedExampleContent(
                title="Find the gradient",
                setup="Use the two plotted points to find the slope.",
                steps=[
                    WorkedStep(label="Step 1", content="Mark the rise and run."),
                    WorkedStep(label="Step 2", content="Compute the ratio."),
                ],
                conclusion="The gradient is the rise divided by the run.",
            )
        ),
        template_contract=_contract(optional=["diagram-block"]),
        style_context=_style_context(),
    )

    slot = next(slot for slot in plan.slots if slot.block_target == "worked_example")
    assert slot.sizing == "compact"
    assert slot.problem_index is None
    assert slot.frames[0].target_w == 600
    assert slot.frames[0].target_h == 400
    assert "Use the two plotted points to find the slope." in (slot.content_brief or "")
