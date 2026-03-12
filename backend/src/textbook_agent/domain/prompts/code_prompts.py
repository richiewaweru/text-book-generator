from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_code_prompt(section: SectionSpec, content: SectionContent) -> str:
    """Build the system prompt for the Code Generator node."""
    return compose_prompt(
        "code_generator",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are generating a code example for a textbook section.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT CONTEXT:
- Plain explanation: {content.plain_explanation}
- Worked example: {content.worked_example}
- Common misconception: {content.common_misconception}

Return only valid JSON matching the SectionCode schema.
The example should be runnable and pedagogically aligned to the section.
Keep every code line at 80 characters or fewer.
Use comments to explain why a step matters, not to narrate obvious syntax.
Do not include commented-out code.
""",
    )
