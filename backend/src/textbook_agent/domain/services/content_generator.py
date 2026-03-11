from pydantic import BaseModel

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from .node_base import PipelineNode


class ContentGeneratorInput(BaseModel):
    """Combined input for the Content Generator node."""

    section: SectionSpec
    profile: LearnerProfile


class ContentGeneratorNode(PipelineNode[ContentGeneratorInput, SectionContent]):
    """Node 2: Generates content for a single section."""

    input_schema = ContentGeneratorInput
    output_schema = SectionContent

    async def run(self, input_data: ContentGeneratorInput) -> SectionContent:
        raise NotImplementedError
