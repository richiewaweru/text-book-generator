from __future__ import annotations

from pipeline.media.types import VisualFrame, VisualSlot
from pipeline.state import StyleContext

SURFACE_TO_DIAGRAM_STYLE: dict[str, str] = {
    "crisp": "clean lines, sharp edges, professional weight strokes, minimal decoration",
    "soft": "slightly rounded corners, gentle stroke weight, warm and readable",
    "minimal": "outline only, no fills, bare essentials, maximum whitespace",
}

PALETTE_TO_STROKE: dict[str, str] = {
    "navy, sky, parchment": "use navy (#1e3a5f) for primary elements, sky blue (#7eb8d4) for secondary, no fills",
    "sand, amber, ink": "use ink (#2c2416) for all strokes, amber (#d97706) for emphasis only",
    "sage, pine, cream": "use pine (#2d4a2d) for primary strokes, sage (#7a9e7a) for secondary",
    "ink, ivory, signal amber": "use high-contrast ink (#111) for all strokes, amber (#f59e0b) for alerts only",
    "white, slate, graphite": "use graphite (#4b5563) for all strokes, no fills whatsoever",
}

TYPOGRAPHY_TO_LABELS: dict[str, str] = {
    "standard": "12px labels, normal weight, standard spacing",
    "reading-support": "14px labels, slightly bolder, generous spacing between elements",
}

COMPLEXITY_TO_DETAIL: dict[str, str] = {
    "simplified": "3-4 elements max, large labels, no sub-labels",
    "standard": "up to 6 labelled elements, clear hierarchy",
    "detailed": "up to 8 elements, can include sub-labels",
}


def build_diagram_style_instruction(ctx: StyleContext) -> str:
    style = SURFACE_TO_DIAGRAM_STYLE.get(ctx.surface_style, SURFACE_TO_DIAGRAM_STYLE["crisp"])
    stroke = PALETTE_TO_STROKE.get(ctx.palette, "use dark grey (#374151) for all strokes")
    labels = TYPOGRAPHY_TO_LABELS.get(ctx.typography, TYPOGRAPHY_TO_LABELS["standard"])
    detail = COMPLEXITY_TO_DETAIL.get(ctx.diagram_complexity(), COMPLEXITY_TO_DETAIL["standard"])

    return f"""Visual style: {style}
Colour: {stroke}
Labels: {labels}
Complexity: {detail}"""


def build_diagram_system_prompt(ctx: StyleContext, *, sizing: str = "full") -> str:
    style_instruction = build_diagram_style_instruction(ctx)
    compact_guidance = (
        "- Keep compact diagrams focused: one focal relationship, minimal ornament, readable labels."
        if sizing == "compact"
        else "- Use the full canvas deliberately for clear spacing and label readability."
    )

    return f"""You generate raw SVG diagrams for educational textbook sections.
You receive a visual brief and must create the clearest possible classroom diagram.

{style_instruction}

SVG rules:
- Output a complete <svg>...</svg> in svg_content.
- Use viewBox="0 0 600 400".
- You may use: svg, g, defs, marker, path, line, polyline, polygon, rect, circle, ellipse, text, tspan, title, desc.
- Do not use script, foreignObject, iframe, object, embed, canvas, video, audio, or image.
- Do not use external images, external links, href/xlink:href to remote resources, event handlers, or javascript: URLs.
- Do not use style values containing url(...).
- Keep labels readable and inside the canvas.
- Prefer clear instructional diagrams over decorative art.
{compact_guidance}

Pedagogy rules:
- If the brief asks for slope, gradient, rise/run, coordinate, graph, grid, or line: draw a real coordinate/grid-style diagram, not a process flowchart.
- For slope diagrams, include axes or a grid, a slanted line, rise/run markers, and readable labels.
- If the brief asks for comparison: use clear side-by-side visual contrast.
- If the brief asks for process: use ordered arrows and labels.
- If the brief asks for science structures: draw labeled parts.
- If the brief asks for measurement: show measurement arrows and values.

Caption: max 60 words, plain language.
alt_text: max 80 words, describes the diagram for screen readers.

Output a JSON object with exactly these fields:
  svg_content, caption, alt_text, diagram_kind, self_check

Output only valid JSON. No preamble, no markdown fences."""


def build_diagram_user_prompt(
    *,
    section_title: str,
    slot: VisualSlot,
    frame: VisualFrame,
) -> str:
    must_include = ", ".join(frame.must_include) if frame.must_include else "None"
    avoid = ", ".join(frame.avoid) if frame.avoid else "None"
    section_target = slot.block_target in {None, "section"}
    if section_target:
        primary_brief = frame.generation_goal or slot.content_brief or section_title
    else:
        primary_brief = slot.content_brief or frame.generation_goal or section_title
    prompt = f"""Section: {section_title}
Slot type: {slot.slot_type.value}
Sizing: {slot.sizing}
Target block: {slot.block_target or "section"}
Frame label: {frame.label or "n/a"}
Pedagogical intent: {slot.pedagogical_intent}
Content brief: {primary_brief}
Caption to support: {slot.caption}
Reference style: {slot.reference_style.value}
Must include: {must_include}
Avoid: {avoid}

Generate raw SVG that makes the planned concept visually clear.
Keep the result aligned to the slot intent and frame scope only."""

    previous_steps_context = frame.output_placeholders.get("previous_steps_context")
    if previous_steps_context:
        prompt += (
            "\n\nPrevious steps context (maintain visual consistency):\n"
            f"{previous_steps_context}"
        )

    previous_attempt_feedback = frame.output_placeholders.get("previous_attempt_feedback")
    if previous_attempt_feedback:
        prompt += (
            "\n\nPrevious attempt feedback (correct this on the next attempt):\n"
            f"{previous_attempt_feedback}"
        )

    return prompt
