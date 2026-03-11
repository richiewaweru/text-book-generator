from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_diagram_prompt(section: SectionSpec, content: SectionContent) -> str:
    """Build the system prompt for the Diagram Generator node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

You are creating a supporting diagram for a textbook section.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT CONTEXT:
- Hook: {content.hook}
- Plain explanation: {content.plain_explanation}
- Worked example: {content.worked_example}

Produce a self-contained inline SVG and return only valid JSON matching the
SectionDiagram schema.
"""
