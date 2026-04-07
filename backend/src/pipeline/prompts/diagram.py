"""
Prompt builders for the diagram_generator node.

System prompt: fixed per style context (structured spec rules, style instructions).
User prompt: variable per section (title, hook, explanation excerpt).

Style maps translate Lectio preset semantics into diagram instructions.
The pipeline never gets hex values from presets -- it gets semantic
descriptors (palette, surface_style) and translates them here.

Output is a structured DiagramSpec (JSON) rendered client-side, not raw SVG.
"""

from __future__ import annotations

from pipeline.state import StyleContext
from pipeline.types.composition import DiagramPlan
from pipeline.types.section_content import SectionContent


# -- Style translation maps ---------------------------------------------------
# These translate Lectio preset semantics into diagram spec instructions.

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

    return f"""You design diagrams for educational content by outputting structured JSON specs.
The specs are rendered client-side — you do NOT generate SVG or HTML.

{style_instruction}

Diagram types:
- "process-flow": steps connected by arrows (horizontal or vertical)
- "hierarchy": parent-child tree structure
- "compare": side-by-side comparison layout
- "cycle": circular process with repeating steps
- "concept-map": interconnected concepts with labeled relationships

Element placement:
- Use a 600×400 coordinate space (x: 0-600, y: 0-400)
- Default element size: 120×60. Adjust for label length.
- Shapes: "rect", "circle", "diamond", "rounded-rect"
- Set emphasis=true for the most important element(s)

Connections:
- Use from_id/to_id referencing element ids
- Styles: "solid" for primary flow, "dashed" for optional/conditional, "arrow" (default) for directed

Caption: max 60 words, plain language.
alt_text: max 80 words, describes the diagram for screen readers.

Output a JSON object with exactly these fields:
  spec (object with type, title, elements, connections, layout_hint), caption, alt_text

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

Generate a structured diagram spec that makes the core concept visually clear.
Keep to 3-6 elements for clarity. Use meaningful connections."""


# ── Image generation prompts ────────────────────────────────────────────────

_SURFACE_TO_IMAGE_STYLE: dict[str, str] = {
    "crisp": "clean vector illustration, sharp lines",
    "soft": "gentle watercolour style, soft edges",
    "minimal": "minimalist line art, essential elements",
}

_PALETTE_TO_IMAGE_COLOURS: dict[str, str] = {
    "navy, sky, parchment": "navy blue and sky blue professional scheme",
    "sand, amber, ink": "warm sand and amber with dark ink",
    "sage, pine, cream": "sage green and pine natural palette",
    "ink, ivory, signal amber": "high-contrast dark ink with amber accents",
    "white, slate, graphite": "neutral slate and graphite tones",
}


def _translate_style_to_image_keywords(ctx: StyleContext) -> str:
    """Map style context to image generation keywords."""
    style = _SURFACE_TO_IMAGE_STYLE.get(ctx.surface_style, "clean illustration")
    colours = _PALETTE_TO_IMAGE_COLOURS.get(ctx.palette, "neutral educational colours")
    return f"{style}, {colours}, textbook quality"


def build_image_generation_prompt(
    section: SectionContent,
    diagram_plan: DiagramPlan,
    style_context: StyleContext,
) -> str:
    """Build a natural-language prompt for image generation models."""

    visual_style = _translate_style_to_image_keywords(style_context)

    prompt = f"""Educational diagram: {section.header.title}

Concept: {section.hook.body}
Context: {section.explanation.body[:300]}

Visual style: {visual_style}

Requirements:
- Clear, simple composition for textbook
- Educational illustration style
- High contrast, readable
- No text overlays (labels added separately)"""

    if diagram_plan.fallback_from_interaction:
        prompt += f"""

This diagram replaces an interaction that would have shown: {diagram_plan.interaction_intent}
Emphasise these elements: {', '.join(diagram_plan.interaction_elements)}"""

    if diagram_plan.visual_guidance:
        prompt += f"\nVisual approach: {diagram_plan.visual_guidance}"

    if diagram_plan.key_concepts:
        prompt += f"\nFocus on: {', '.join(diagram_plan.key_concepts)}"

    return prompt


def build_series_step_image_prompt(
    *,
    section_title: str,
    step_label: str,
    step_index: int,
    total_steps: int,
    key_concept: str,
    style_context: StyleContext,
) -> str:
    visual_style = _translate_style_to_image_keywords(style_context)

    return (
        f"Educational diagram, step {step_index + 1} of {total_steps}, for {section_title}. "
        f"This step shows: {step_label}. "
        f"Focus on: {key_concept}. "
        f"Style: {visual_style}. "
        "Requirements: white background, textbook quality, clear composition, "
        "no text overlays, visually consistent with the other steps in the same sequence."
    )


def build_hook_image_prompt(
    *,
    section_title: str,
    hook_headline: str,
    hook_body: str,
    style_context: StyleContext,
) -> str:
    visual_style = _translate_style_to_image_keywords(style_context)

    return (
        f"Educational visual anchor for a lesson about {section_title}. "
        f"Hook question: {hook_headline}. "
        f"Context: {hook_body[:200]}. "
        f"Style: {visual_style}, realistic educational illustration, "
        "classroom-appropriate, grounded in a real-world scene, no text overlays."
    )


def build_compare_image_prompts(
    *,
    section: SectionContent,
    diagram_plan: DiagramPlan,
    style_context: StyleContext,
    before_label: str,
    after_label: str,
) -> tuple[str, str]:
    visual_style = _translate_style_to_image_keywords(style_context)
    shared_requirements = (
        f"Educational before-and-after comparison for {section.header.title}. "
        f"Concept: {section.hook.body[:220]}. "
        f"Context: {section.explanation.body[:300]}. "
        f"Style: {visual_style}. "
        "Requirements: textbook quality, no text overlays, same subject, same viewpoint, "
        "same framing, same camera distance, same composition, same background, and same "
        "lighting in both images. Only the pedagogically meaningful change should differ "
        "between the before and after states."
    )

    if diagram_plan.visual_guidance:
        shared_requirements += f" Visual guidance: {diagram_plan.visual_guidance}."
    if diagram_plan.key_concepts:
        shared_requirements += f" Focus on: {', '.join(diagram_plan.key_concepts)}."

    before_prompt = (
        f"{shared_requirements} "
        f"Render the BEFORE state for the comparison, aligned to the label '{before_label}'. "
        "Show the baseline condition before the transformation happens."
    )
    after_prompt = (
        f"{shared_requirements} "
        f"Render the AFTER state for the comparison, aligned to the label '{after_label}'. "
        "Show the transformed condition after the change while preserving the same scene."
    )
    return before_prompt, after_prompt
