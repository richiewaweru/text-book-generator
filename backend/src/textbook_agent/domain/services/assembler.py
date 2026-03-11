from pydantic import BaseModel

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.textbook import RawTextbook
from .node_base import PipelineNode


class AssemblerInput(BaseModel):
    """Combined input for the Assembler node."""

    profile: LearnerProfile
    plan: CurriculumPlan
    sections: list[SectionContent]
    diagrams: list[SectionDiagram]
    code_examples: list[SectionCode]


class AssemblerNode(PipelineNode[AssemblerInput, RawTextbook]):
    """Node 5: Combines all section outputs into a structured textbook.

    Pure Python. No LLM call. Applies reading order from the curriculum plan.
    """

    input_schema = AssemblerInput
    output_schema = RawTextbook
    retry_on_failure = False

    def __init__(self) -> None:
        super().__init__(provider=None)

    async def run(self, input_data: AssemblerInput) -> RawTextbook:
        raise NotImplementedError
