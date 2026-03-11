from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from .base_prompt import BASE_PEDAGOGICAL_RULES


def build_diagram_prompt(section: SectionSpec, content: SectionContent) -> str:
    """Build the system prompt for the Diagram Generator node."""
    raise NotImplementedError
