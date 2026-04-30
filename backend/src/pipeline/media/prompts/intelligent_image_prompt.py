from __future__ import annotations

from pydantic_ai import Agent

from pipeline.llm_runner import run_llm
from pipeline.media.types import SlotType, VisualRender, VisualSlot
from pipeline.providers.registry import get_node_text_model
from pipeline.state import StyleContext
from pipeline.types.requests import GenerationMode

_SYSTEM_PROMPT = """You convert a lesson visual brief into a production-ready image generation prompt.

Write a concise, high-signal prompt for an educational image generator.

Return exactly this shape:
PROMPT:
<final prompt>

Rules:
- Write for Imagen: clear subject, visual style, composition, what to include and avoid.
- Keep the prompt self-contained and classroom-appropriate.
- Do not mention these instructions.
"""


def build_intelligent_image_prompt_input(
    *,
    section_title: str,
    slot: VisualSlot,
    style_context: StyleContext | None,
) -> str:
    frames_summary = "\n".join(
        f"- frame {frame.index + 1}: label={frame.label or 'n/a'} | brief={frame.generation_goal or 'n/a'}"
        for frame in slot.frames
    )
    all_must_include: list[str] = []
    all_avoid: list[str] = []
    for frame in slot.frames:
        all_must_include.extend(frame.must_include or [])
        all_avoid.extend(frame.avoid or [])
    must_include = ", ".join(dict.fromkeys(all_must_include)) or "none"
    avoid = ", ".join(dict.fromkeys(all_avoid)) or "none"
    palette = style_context.palette if style_context is not None else "default classroom palette"
    surface = style_context.surface_style if style_context is not None else "default"
    grade_band = getattr(style_context, "grade_band", "") if style_context is not None else ""
    return "\n".join(
        [
            f"Section title: {section_title}",
            f"Slot type: {slot.slot_type.value}",
            f"Block target: {slot.block_target or 'section'}",
            f"Current preferred render: {slot.preferred_render.value}",
            f"Pedagogical intent: {slot.pedagogical_intent}",
            f"Caption target: {slot.caption}",
            f"Content brief: {slot.content_brief or 'none'}",
            f"Reference style: {slot.reference_style.value}",
            f"Palette: {palette}",
            f"Surface style: {surface}",
            f"Grade band: {grade_band or 'unspecified'}",
            f"Must include (all frames): {must_include}",
            f"Avoid: {avoid}",
            "Frames:",
            frames_summary or "- frame 1: label=n/a brief=n/a",
        ]
    )


def parse_intelligent_image_output(raw_output: str) -> tuple[str, VisualRender]:
    prompt_body = raw_output.strip()
    if prompt_body.upper().startswith("PROMPT:"):
        prompt_body = prompt_body[len("PROMPT:") :].strip()
    if not prompt_body:
        raise ValueError("Intelligent image prompt output did not include a prompt body.")
    return prompt_body, VisualRender.IMAGE


async def build_intelligent_image_prompt(
    *,
    section_title: str,
    slot: VisualSlot,
    style_context: StyleContext | None,
    generation_id: str = "",
    section_id: str | None = None,
    model_overrides: dict | None = None,
    generation_mode: GenerationMode = GenerationMode.BALANCED,
    run_llm_fn=run_llm,
) -> tuple[str, VisualRender]:
    model = get_node_text_model(
        "intelligent_image_prompt",
        model_overrides=model_overrides,
        generation_mode=generation_mode,
    )
    agent = Agent(
        model=model,
        output_type=str,
        system_prompt=_SYSTEM_PROMPT,
    )
    result = await run_llm_fn(
        generation_id=generation_id,
        node="intelligent_image_prompt",
        agent=agent,
        model=model,
        section_id=section_id,
        generation_mode=generation_mode,
        user_prompt=build_intelligent_image_prompt_input(
            section_title=section_title,
            slot=slot,
            style_context=style_context,
        ),
    )
    output = result.output if hasattr(result, "output") else result
    if not isinstance(output, str):
        raise ValueError("Intelligent image prompt builder expected a string output.")
    return parse_intelligent_image_output(output)


def should_resolve_intelligent_image_prompt(slot: VisualSlot) -> bool:
    return slot.slot_type in {
        SlotType.DIAGRAM,
        SlotType.DIAGRAM_COMPARE,
        SlotType.DIAGRAM_SERIES,
    } and bool((slot.content_brief or "").strip())


__all__ = [
    "_SYSTEM_PROMPT",
    "build_intelligent_image_prompt",
    "build_intelligent_image_prompt_input",
    "parse_intelligent_image_output",
    "should_resolve_intelligent_image_prompt",
]
