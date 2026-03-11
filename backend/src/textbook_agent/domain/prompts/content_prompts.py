from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_content_prompt(section: SectionSpec, profile: LearnerProfile) -> str:
    """Build the system prompt for the Content Generator node."""
    raise NotImplementedError
