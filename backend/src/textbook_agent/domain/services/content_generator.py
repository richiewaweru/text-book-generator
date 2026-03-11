import asyncio

from pydantic import BaseModel

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.prompts.content_prompts import build_content_prompt
from .node_base import PipelineNode


class ContentGeneratorInput(BaseModel):
    """Combined input for the Content Generator node."""

    section: SectionSpec
    profile: GenerationContext


class ContentGeneratorNode(PipelineNode[ContentGeneratorInput, SectionContent]):
    """Node 2: Generates content for a single section."""

    input_schema = ContentGeneratorInput
    output_schema = SectionContent

    async def run(self, input_data: ContentGeneratorInput) -> SectionContent:
        prompt = build_content_prompt(input_data.section, input_data.profile)
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Write section: {input_data.section.title}",
            response_schema=SectionContent,
        )
