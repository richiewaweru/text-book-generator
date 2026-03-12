from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.prompts.planner_prompts import _learner_block

from .base_prompt import BASE_PEDAGOGICAL_AND_FORMATTING_RULES, compose_prompt


def build_content_prompt(section: SectionSpec, profile: GenerationContext) -> str:
    """Build the system prompt for the Content Generator node."""
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
