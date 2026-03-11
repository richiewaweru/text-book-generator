import asyncio

from pydantic import BaseModel

from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.prompts.code_prompts import build_code_prompt
from .node_base import PipelineNode


class CodeGeneratorInput(BaseModel):
    """Combined input for the Code Generator node."""

    section: SectionSpec
    content: SectionContent


class CodeGeneratorNode(PipelineNode[CodeGeneratorInput, SectionCode]):
    """Node 4: Generates code examples for sections that need them."""

    input_schema = CodeGeneratorInput
    output_schema = SectionCode

    async def run(self, input_data: CodeGeneratorInput) -> SectionCode:
        prompt = build_code_prompt(input_data.section, input_data.content)
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Generate a code example for section: {input_data.section.title}",
            response_schema=SectionCode,
        )
