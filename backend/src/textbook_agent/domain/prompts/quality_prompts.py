from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_quality_prompt(textbook: RawTextbook, plan: CurriculumPlan) -> str:
    """Build the system prompt for the Quality Checker node."""
    raise NotImplementedError
