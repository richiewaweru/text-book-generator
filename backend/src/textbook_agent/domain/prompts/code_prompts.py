from textbook_agent.domain.entities.correction_context import CodeCorrectionContext
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def _render_issue_block(issues: list) -> str:
    return "\n".join(
        f"- {issue.issue_type}: {issue.description}" for issue in issues
    ) or "- No issues supplied."


def build_code_prompt(
    section: SectionSpec,
    content: SectionContent,
    correction_context: CodeCorrectionContext | None = None,
) -> str:
    """Build the system prompt for the Code Generator node."""
    if correction_context is not None:
        return compose_prompt(
            "code_generator_correction",
            BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
            f"""
You are correcting an existing code example for a textbook section.

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CONTENT CONTEXT:
- Plain explanation: {content.plain_explanation}
- Worked example: {content.worked_example}
- Common misconception: {content.common_misconception}

CURRENT CODE JSON:
{correction_context.original_code.model_dump_json(indent=2)}

ISSUES TO FIX:
{_render_issue_block(correction_context.issues)}

Correction rules:
- Fix only the listed issues.
- Preserve the current teaching goal and overall example shape.
- Do not introduce new concepts or extra scaffolding not required by the issues.
- Return only valid JSON matching the SectionCode schema.
""",
        )
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
