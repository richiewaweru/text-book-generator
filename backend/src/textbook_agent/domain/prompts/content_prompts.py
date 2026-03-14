from textbook_agent.domain.entities.correction_context import ContentCorrectionContext
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.prompts.planner_prompts import _learner_block

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def _render_issue_block(issues: list) -> str:
    return "\n".join(
        f"- {issue.issue_type}: {issue.description}" for issue in issues
    ) or "- No issues supplied."


def build_content_prompt(
    section: SectionSpec,
    profile: GenerationContext,
    correction_context: ContentCorrectionContext | None = None,
) -> str:
    """Build the system prompt for the Content Generator node."""
    if correction_context is not None:
        return compose_prompt(
            "content_generator_correction",
            BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
            f"""
You are correcting an existing section for a personalized {profile.subject} textbook.

LEARNER:
{_learner_block(profile)}
- Preferred notation: {profile.language.value}

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}

CURRENT SECTION JSON:
{correction_context.original_content.model_dump_json(indent=2)}

ISSUES TO FIX:
{_render_issue_block(correction_context.issues)}

Correction rules:
- Fix only the listed issues.
- Preserve the section's current scope, examples, and overall structure.
- Do not introduce new concepts, extra examples, or broader rewrites.
- Keep the output consistent with the original section unless a listed issue requires a change.
- Return only valid JSON matching the SectionContent schema.
""",
        )
    return compose_prompt(
        "content_generator",
        BASE_PEDAGOGICAL_AND_FORMATTING_RULES,
        f"""
You are writing a single section for a personalized {profile.subject} textbook.

LEARNER:
{_learner_block(profile)}
- Preferred notation: {profile.language.value}

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}
- Estimated depth: {section.estimated_depth.value}
- Needs diagram: {section.needs_diagram}
- Needs code: {section.needs_code}

Personalization guidance:
- Draw analogies and examples from the learner's interests where relevant.
- Adapt explanation style to the learner's preferred learning style.
- Use vocabulary appropriate for the learner's education level and age.

Schema contract:
- Return only valid JSON matching the SectionContent schema.
- Fill all 11 SectionContent fields.
- practice_problems must contain exactly three items with warm, medium, and cold difficulties.
- prerequisites_block, interview_anchor, and think_prompt should be non-empty when they add learner value.
- connection_forward must set up the next section in one concise sentence.
""",
    )
