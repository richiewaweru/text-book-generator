from __future__ import annotations

from pipeline.media.prompts.diagram_prompts import (
    build_diagram_system_prompt,
    build_diagram_user_prompt,
)
from pipeline.media.prompts.image_prompts import (
    build_compare_image_prompts,
    build_image_generation_prompt,
)
from pipeline.media.types import VisualFrame, VisualSlot
from pipeline.state import StyleContext


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


def test_diagram_prompt_uses_slot_and_frame_contract() -> None:
    slot = VisualSlot(
        slot_id="diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        pedagogical_intent="Explain the structure clearly.",
        caption="Support the final classroom caption.",
        frames=[
            VisualFrame(
                slot_id="diagram",
                index=0,
                label="Core view",
                generation_goal="Show the idea clearly.",
                must_include=["slope", "rise over run"],
                avoid=["text overlays"],
            )
        ],
    )

    prompt = build_diagram_user_prompt(
        section_title="Rates of change",
        slot=slot,
        frame=slot.frames[0],
    )

    assert "Pedagogical intent: Explain the structure clearly." in prompt
    assert "Must include: slope, rise over run" in prompt


def test_diagram_system_prompt_includes_safe_zone_and_type_guard() -> None:
    prompt = build_diagram_system_prompt(_style_context())

    assert "SAFE ZONE" in prompt
    assert "Valid placement range: x 40-560, y 50-360." in prompt
    assert "Do not use \"concept-map\" for mathematical, spatial, or graphical content." in prompt


def test_diagram_system_prompt_uses_compact_coordinate_space() -> None:
    prompt = build_diagram_system_prompt(_style_context(), sizing="compact")

    assert "Use a 400x300 coordinate space." in prompt
    assert "2-4 elements only" in prompt


def test_image_prompts_consume_frame_data_only() -> None:
    slot = VisualSlot(
        slot_id="diagram_compare",
        slot_type="diagram_compare",
        required=True,
        preferred_render="image",
        pedagogical_intent="Compare the two states.",
        caption="Use the final compare caption.",
        frames=[
            VisualFrame(
                slot_id="diagram_compare",
                index=0,
                label="Before",
                generation_goal="Render the before state.",
                must_include=["before state"],
                avoid=["text overlays"],
            ),
            VisualFrame(
                slot_id="diagram_compare",
                index=1,
                label="After",
                generation_goal="Render the after state.",
                must_include=["after state"],
                avoid=["text overlays"],
            ),
        ],
    )

    single_prompt = build_image_generation_prompt(
        section_title="Rates of change",
        slot=slot,
        frame=slot.frames[0],
        style_context=_style_context(),
    )
    before_prompt, after_prompt = build_compare_image_prompts(
        section_title="Rates of change",
        slot=slot,
        before_frame=slot.frames[0],
        after_frame=slot.frames[1],
        style_context=_style_context(),
    )

    assert "Content brief: Render the before state." in single_prompt
    assert "'Before'" in before_prompt
    assert "'After'" in after_prompt


def test_media_prompts_include_content_brief_and_compact_sizing() -> None:
    slot = VisualSlot(
        slot_id="practice-0-diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        sizing="compact",
        block_target="practice",
        problem_index=0,
        content_brief="Show a small coordinate grid with a line through (0,1) and (4,9).",
        pedagogical_intent="Support the selected practice problem.",
        caption="Practice support diagram.",
        frames=[
            VisualFrame(
                slot_id="practice-0-diagram",
                index=0,
                label="Practice problem 1",
                generation_goal="Fallback generation goal.",
                must_include=["coordinate grid", "line"],
                avoid=["text overlays"],
                target_w=600,
                target_h=400,
            )
        ],
    )

    image_prompt = build_image_generation_prompt(
        section_title="Rates of change",
        slot=slot,
        frame=slot.frames[0],
        style_context=_style_context(),
    )
    diagram_prompt = build_diagram_user_prompt(
        section_title="Rates of change",
        slot=slot,
        frame=slot.frames[0],
    )

    assert "Content brief: Show a small coordinate grid" in image_prompt
    assert "Sizing: compact" in image_prompt
    assert "Target aspect ratio: 600:400 - optimise composition for this shape" in image_prompt
    assert "Content brief: Show a small coordinate grid" in diagram_prompt
    assert "Target block: practice" in diagram_prompt
