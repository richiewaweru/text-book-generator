from pydantic import BaseModel

from textbook_agent.domain.entities.curriculum_plan import SectionSpec
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from .node_base import PipelineNode


class DiagramGeneratorInput(BaseModel):
    """Combined input for the Diagram Generator node."""

    section: SectionSpec
    content: SectionContent


class DiagramGeneratorNode(PipelineNode[DiagramGeneratorInput, SectionDiagram]):
    """Node 3: Generates SVG diagrams for sections that need visuals."""

    input_schema = DiagramGeneratorInput
    output_schema = SectionDiagram

    async def run(self, input_data: DiagramGeneratorInput) -> SectionDiagram:
        raise NotImplementedError
