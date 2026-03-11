from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_content_prompt(section: SectionSpec, profile: LearnerProfile) -> str:
    """Build the system prompt for the Content Generator node."""
    return f"""
{BASE_PEDAGOGICAL_RULES}

You are writing a single section for a personalized {profile.subject} textbook.

LEARNER:
- Age: {profile.age}
- Depth requested: {profile.depth.value}
- Preferred notation: {profile.language.value}
- Context: {profile.context}

SECTION:
- ID: {section.id}
- Title: {section.title}
- Learning objective: {section.learning_objective}
- Estimated depth: {section.estimated_depth.value}
- Needs diagram: {section.needs_diagram}
- Needs code: {section.needs_code}

Write the section content so it strictly conforms to the SectionContent schema.
Return only valid JSON matching the SectionContent contract.
"""
