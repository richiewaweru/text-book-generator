from textbook_agent.domain.entities.correction_context import DiagramCorrectionContext
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def _render_issue_block(issues: list) -> str:
    return "\n".join(
        f"- {issue.issue_type}: {issue.description}" for issue in issues
    ) or "- No issues supplied."


def build_diagram_prompt(
    section: SectionSpec,
    content: SectionContent,
    correction_context: DiagramCorrectionContext | None = None,
) -> str:
    """Build the system prompt for the Diagram Generator node."""
    if correction_context is not None:
        return compose_prompt(
            "diagram_generator_correction",
            BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
            f"""
You are correcting an existing supporting diagram for a textbook section.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT CONTEXT:
- Hook: {content.hook}
- Plain explanation: {content.plain_explanation}
- Formal definition: {content.formal_definition}
- Worked example: {content.worked_example}

CURRENT DIAGRAM JSON:
{correction_context.original_diagram.model_dump_json(indent=2)}

ISSUES TO FIX:
{_render_issue_block(correction_context.issues)}

Correction rules:
- Fix only the listed issues.
- Preserve the current diagram concept and pedagogical intent.
- Do not add extra explanatory content beyond what is needed to resolve the issues.
- Return only valid JSON matching the SectionDiagram schema.
""",
        )
    return compose_prompt(
        "diagram_generator",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are creating a supporting diagram for a textbook section.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT CONTEXT:
- Hook: {content.hook}
- Plain explanation: {content.plain_explanation}
- Formal definition: {content.formal_definition}
- Worked example: {content.worked_example}

SVG requirements:
- Return only valid JSON matching the SectionDiagram schema.
- svg_markup must be a self-contained inline SVG with explicit width, height, and viewBox attributes.
- Define arrow markers inside <defs> when arrows are used.
- Use IBM Plex Mono for diagram labels.
- Keep label text at 12px or larger.
""",
    )
