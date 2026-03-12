from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_diagram_prompt(section: SectionSpec, content: SectionContent) -> str:
    """Build the system prompt for the Diagram Generator node."""
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
