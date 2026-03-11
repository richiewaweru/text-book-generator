from pydantic import BaseModel

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.section_content import SectionContent
from textbook_agent.domain.entities.section_diagram import SectionDiagram
from textbook_agent.domain.entities.section_code import SectionCode
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.exceptions import PipelineError
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
        content_map: dict[str, SectionContent] = {
            s.section_id: s for s in input_data.sections
        }
        diagram_map: dict[str, SectionDiagram] = {
            d.section_id: d for d in input_data.diagrams
        }
        code_map: dict[str, SectionCode] = {
            c.section_id: c for c in input_data.code_examples
        }

        ordered_sections: list[SectionContent] = []
        ordered_diagrams: list[SectionDiagram] = []
        ordered_code: list[SectionCode] = []

        for section_id in input_data.plan.reading_order:
            if section_id not in content_map:
                raise PipelineError(
                    node_name="AssemblerNode",
                    reason=f"Missing content for section '{section_id}' in reading_order",
                )
            ordered_sections.append(content_map[section_id])
            if section_id in diagram_map:
                ordered_diagrams.append(diagram_map[section_id])
            if section_id in code_map:
                ordered_code.append(code_map[section_id])

        return RawTextbook(
            subject=input_data.plan.subject,
            profile=input_data.profile,
            plan=input_data.plan,
            sections=ordered_sections,
            diagrams=ordered_diagrams,
            code_examples=ordered_code,
        )
