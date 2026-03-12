from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.prompts.planner_prompts import _learner_block
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_content_prompt(section: SectionSpec, profile: GenerationContext) -> str:
    """Build the system prompt for the Content Generator node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

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

Personalisation guidance:
- Draw analogies and examples from the learner's interests where relevant.
- Adapt explanation style to the learner's preferred learning style.
- Use vocabulary appropriate for the learner's education level and age.

Write the section content so it strictly conforms to the SectionContent schema.
Return only valid JSON matching the SectionContent contract.
"""
