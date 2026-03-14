from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_inline_quality_prompt(
    section: SectionSpec,
    content: SectionContent,
    diagram: SectionDiagram | None = None,
    code_example: SectionCode | None = None,
) -> str:
    """Build the system prompt for per-section inline quality review."""

    diagram_block = (
        f"- Diagram caption: {diagram.caption}\n- Diagram type: {diagram.diagram_type}"
        if diagram is not None
        else "- No diagram for this section."
    )
    code_block = (
        f"- Code language: {code_example.language}\n- Code explanation: {code_example.explanation}"
        if code_example is not None
        else "- No code example for this section."
    )

    return compose_prompt(
        "inline_quality_checker",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are reviewing one textbook section immediately after generation.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT:
- Hook: {content.hook}
- Plain explanation: {content.plain_explanation}
- Formal definition: {content.formal_definition}
- Worked example: {content.worked_example}
- Common misconception: {content.common_misconception}

DIAGRAM:
{diagram_block}

CODE:
{code_block}

Focus only on section-local issues that can be fixed without considering other sections.

Allowed issue scopes:
- Use only "section".

Issue type naming:
- Prefix content issues with "content_"
- Prefix diagram issues with "diagram_"
- Prefix code issues with "code_"

Severity rules:
- "error" only for issues that would materially confuse the learner in this section
- "warning" for cosmetic or non-blocking issues

Return only valid JSON matching the QualityReport schema.
""",
    )
