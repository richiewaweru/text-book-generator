from __future__ import annotations

from pipeline.media.prompts.intelligent_image_prompt import (
    _SYSTEM_PROMPT as IMAGE_INTENT_SYSTEM_PROMPT,
    build_intelligent_image_prompt_input,
    parse_intelligent_image_output,
)
from pipeline.media.prompts.image_prompts import (
    build_compare_image_prompts,
    build_image_generation_prompt,
)
from pipeline.media.types import VisualFrame, VisualSlot
from pipeline.state import StyleContext


def _style_context(**overrides) -> StyleContext:
    payload = {
        "preset_id": "blue-classroom",
        "palette": "navy, sky, parchment",
        "surface_style": "crisp",
        "density": "standard",
        "typography": "standard",
        "template_id": "guided-concept-path",
        "template_family": "guided-concept",
        "interaction_level": "medium",
        "grade_band": "secondary",
        "learner_fit": "general",
    }
    payload.update(overrides)
    return StyleContext(**payload)


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

    assert "Content brief: Show a small coordinate grid" in image_prompt
    assert "Sizing: compact" in image_prompt
    assert "Target aspect ratio: 600:400 - optimise composition for this shape" in image_prompt


def test_build_image_generation_prompt_prefers_frame_goal_for_section_slot() -> None:
    slot = VisualSlot(
        slot_id="section-diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="image",
        block_target="section",
        content_brief="Use a sequence visual.",
        pedagogical_intent="Show positive slope.",
        caption="Positive and Negative Slopes",
        frames=[],
    )
    frame = VisualFrame(
        slot_id="section-diagram-series",
        index=0,
        label="Step 1",
        generation_goal="A coordinate plane showing a rising line labeled slope=3/4.",
    )

    prompt = build_image_generation_prompt(
        section_title="See Positive and Negative Slopes",
        slot=slot,
        frame=frame,
        style_context=_style_context(grade_band="middle_school"),
    )

    assert "coordinate plane" in prompt
    assert "Use a sequence visual" not in prompt
    assert "Clean educational illustration, moderate detail" in prompt


def test_build_image_generation_prompt_wraps_override_brief() -> None:
    slot = VisualSlot(
        slot_id="diagram",
        slot_type="diagram",
        required=True,
        preferred_render="image",
        pedagogical_intent="Show the concept.",
        caption="Caption",
        frames=[],
    )
    frame = VisualFrame(
        slot_id="diagram",
        index=0,
        generation_goal="Fallback goal.",
        must_include=["axis"],
    )

    prompt = build_image_generation_prompt(
        section_title="Rates of change",
        slot=slot,
        frame=frame,
        style_context=_style_context(),
        override_brief="Custom intelligent prompt body.",
    )

    assert "Content brief: Custom intelligent prompt body." in prompt
    assert "Must include: axis" in prompt
    assert "Requirements:" in prompt


def test_intelligent_image_prompt_includes_all_frame_briefs() -> None:
    slot = VisualSlot(
        slot_id="diagram_series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Positive and Negative Slopes",
        frames=[
            VisualFrame(
                slot_id="diagram_series",
                index=0,
                label="Step 1",
                generation_goal="Frame 1 brief here.",
                must_include=["axis"],
            ),
            VisualFrame(
                slot_id="diagram_series",
                index=1,
                label="Step 2",
                generation_goal="Frame 2 brief here.",
                must_include=["line"],
                avoid=["clutter"],
            ),
        ],
    )

    result = build_intelligent_image_prompt_input(
        section_title="See Slopes",
        slot=slot,
        style_context=_style_context(grade_band="middle_school"),
    )

    assert "Block target: section" in result
    assert "Grade band: middle_school" in result
    assert "Must include (all frames): axis, line" in result
    assert "Avoid: clutter" in result
    assert "Frame 1 brief here." in result
    assert "Frame 2 brief here." in result


def test_intelligent_image_prompt_parser_returns_image_prompt() -> None:
    prompt, render_mode = parse_intelligent_image_output(
        "PROMPT:\nDraw a clear classroom image of a coordinate plane with a labeled tangent line."
    )

    assert render_mode == "image"
    assert "coordinate plane" in prompt


def test_intelligent_image_prompt_system_prompt_requires_prompt_shape() -> None:
    assert "PROMPT:" in IMAGE_INTENT_SYSTEM_PROMPT
    assert "RENDER_MODE" not in IMAGE_INTENT_SYSTEM_PROMPT
