"""
Prompt builders for the composition_planner node.

System prompt: explains the composition task, includes interaction catalog,
               describes the expected JSON output schema.
User prompt:   per-section context with content excerpts, usage stats,
               and diversity hints.
"""

from __future__ import annotations

from pipeline.catalogs.interaction_catalog import get_interaction_guidance
from pipeline.types.section_content import SectionContent
from pipeline.types.template_contract import TemplateContractSummary


def build_composition_system_prompt(contract: TemplateContractSummary) -> str:
    """Build system prompt explaining the composition task."""

    return f"""You are a pedagogical compositor for educational textbook sections.

Your task is to decide what visual and interactive elements to include in a section,
choosing from the available interaction types or falling back to a static diagram.

TEMPLATE: {contract.name} ({contract.family})
INTERACTION LEVEL: {contract.interaction_level}

{get_interaction_guidance()}

DESIGN PRINCIPLES:
1. Prefer interactions over static diagrams when the concept is manipulable.
2. Use diagram fallback only when interaction isn't viable for the concept.
3. Multiple interactions are allowed (up to 2 per section) if they serve distinct purposes.
4. Simple interactions are fine if pedagogically sound -- complexity is not a goal.
5. Manipulation must reveal insight, not just illustrate.
6. Avoid repeating the same interaction type across consecutive sections.

OUTPUT: Respond with a JSON object. No preamble, no markdown fences.
The JSON must have exactly these fields:

{{
    "diagram": {{
        "enabled": bool,
        "reasoning": "why diagram is or isn't needed",
        "diagram_type": "process" | "timeline" | "comparison" | "concept_map" | "spatial" | null,
        "key_concepts": ["concept1", "concept2"],
        "visual_guidance": "optional visual approach hint" | null,
        "fallback_from_interaction": bool,
        "interaction_intent": "what interaction would have shown" | null,
        "interaction_elements": ["element1"] | []
    }},
    "interactions": [
        {{
            "enabled": true,
            "reasoning": "why this supports learning",
            "interaction_type": "graph_slider" | "equation_reveal" | "timeline_scrubber" | "geometry_explorer" | "probability_tree" | "molecule_viewer",
            "anchor_block": "explanation" | "worked_example" | "timeline" | "process",
            "manipulable_element": "what learner controls",
            "response_element": "what changes in response",
            "pedagogical_payoff": "what insight emerges from manipulation",
            "complexity": "simple" | "moderate" | "complex"
        }}
    ],
    "reasoning": "overall composition strategy",
    "confidence": "low" | "medium" | "high"
}}"""


def build_composition_user_prompt(
    section: SectionContent,
    subject: str,
    grade_band: str,
    interaction_usage: dict[str, int],
) -> str:
    """Build user prompt with section content and context."""

    objective = section.header.objective or section.hook.headline
    usage_stats = _format_usage_stats(interaction_usage)

    return f"""SECTION CONTENT:

Title: {section.header.title}
Objective: {objective}
Hook: {section.hook.headline}
Explanation: {section.explanation.body[:400]}

CONTEXT:
- Subject: {subject}
- Grade: {grade_band}

INTERACTION USAGE SO FAR:
{usage_stats}

TASK:
1. Analyze this section for manipulable elements (variables, parameters, processes).
2. Design interaction(s) if the concept is manipulable.
3. Fall back to diagram if no meaningful interaction is possible.
4. Extract key concepts for visual emphasis.

Respond with the JSON object described in the system prompt."""


def _format_usage_stats(interaction_usage: dict[str, int]) -> str:
    """Format usage stats for the prompt to encourage diversity."""
    if not interaction_usage:
        return "No interactions yet. This is the first section."

    total = sum(interaction_usage.values())
    lines = []
    for itype, count in sorted(interaction_usage.items(), key=lambda x: -x[1]):
        pct = (count / total) * 100
        lines.append(f"  - {itype}: {count} ({pct:.0f}%)")
    lines.append("\nPrefer variety to avoid monotony.")
    return "\n".join(lines)
