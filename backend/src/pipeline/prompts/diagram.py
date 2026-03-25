"""
Prompt builders for the diagram_generator node.

System prompt: fixed per style context (SVG rules, style instructions).
User prompt: variable per section (title, hook, explanation excerpt).

Style maps translate Lectio preset semantics into diagram instructions.
The pipeline never gets hex values from presets -- it gets semantic
descriptors (palette, surface_style) and translates them here.
"""

from __future__ import annotations

from pipeline.state import StyleContext


# -- Style translation maps ---------------------------------------------------
# These translate Lectio preset semantics into SVG diagram instructions.

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
    "simplified": "3-4 elements max, large labels, no sub-labels, no arrows unless essential",
    "standard": "up to 6 labelled elements, clear hierarchy, arrows for relationships",
    "detailed": "up to 8 elements, can include sub-labels, formal notation where appropriate",
}


def build_diagram_style_instruction(ctx: StyleContext) -> str:
    """
    Translate StyleContext into a concrete diagram instruction string.
    Ensures visual consistency across all sections -- every diagram call
    receives identical style instructions.
    """
    style = SURFACE_TO_DIAGRAM_STYLE.get(ctx.surface_style, SURFACE_TO_DIAGRAM_STYLE["crisp"])
    stroke = PALETTE_TO_STROKE.get(ctx.palette, "use dark grey (#374151) for all strokes")
    labels = TYPOGRAPHY_TO_LABELS.get(ctx.typography, TYPOGRAPHY_TO_LABELS["standard"])
    detail = COMPLEXITY_TO_DETAIL.get(ctx.diagram_complexity(), COMPLEXITY_TO_DETAIL["standard"])

    return f"""Visual style: {style}
Colour: {stroke}
Labels: {labels}
Complexity: {detail}"""


def build_diagram_system_prompt(ctx: StyleContext) -> str:
    style_instruction = build_diagram_style_instruction(ctx)

    return f"""You generate SVG diagrams for educational content.

{style_instruction}

SVG rules:
- viewBox="0 0 600 400" always
- xmlns="http://www.w3.org/2000/svg" always
- No external resources, no <image> tags, no CSS classes
- All styling via inline attributes (stroke, fill, font-size)
- Text must be readable at 300px wide (minimum 11px font-size)
- Caption: max 60 words, plain language
- alt_text: max 80 words, describes the diagram for screen readers

Output a JSON object with exactly these fields:
  svg_content, caption, alt_text

Output only valid JSON. No preamble, no markdown fences."""


def build_diagram_user_prompt(
    section_title: str,
    hook_body: str,
    explanation_excerpt: str,
    diagram_slot: str,
    diagram_type: str | None = None,
    key_concepts: list[str] | None = None,
    visual_guidance: str | None = None,
) -> str:
    details = ""
    if diagram_type:
        details += f"\nPreferred diagram type: {diagram_type}"
    if key_concepts:
        details += f"\nKey concepts to visualize: {', '.join(key_concepts)}"
    if visual_guidance:
        details += f"\nVisual guidance: {visual_guidance}"

    return f"""Section: {section_title}
Concept summary: {hook_body}
Explanation (first 200 words): {explanation_excerpt[:800]}
Diagram slot: {diagram_slot}
{details}

Generate a diagram that makes the core concept visually clear."""
