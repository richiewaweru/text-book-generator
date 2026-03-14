import asyncio

from pydantic import BaseModel

from textbook_agent.domain.entities.correction_context import DiagramCorrectionContext
from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.prompts.diagram_prompts import build_diagram_prompt
from .node_base import PipelineNode


class DiagramGeneratorInput(BaseModel):
    """Combined input for the Diagram Generator node."""

    section: SectionSpec
    content: SectionContent
    correction_context: DiagramCorrectionContext | None = None


class DiagramGeneratorNode(PipelineNode[DiagramGeneratorInput, SectionDiagram]):
    """Node 3: Generates SVG diagrams for sections that need visuals."""

    input_schema = DiagramGeneratorInput
    output_schema = SectionDiagram

    def __init__(self, provider=None, model_override: str | None = None) -> None:
        super().__init__(provider=provider)
        self.model_override = model_override

    async def run(self, input_data: DiagramGeneratorInput) -> SectionDiagram:
        prompt = build_diagram_prompt(
            input_data.section,
            input_data.content,
            correction_context=input_data.correction_context,
        )
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt=f"Create a diagram for section: {input_data.section.title}",
            response_schema=SectionDiagram,
            model=self.model_override,
        )
