from pydantic import BaseModel

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityReport
from .node_base import PipelineNode


class QualityCheckerInput(BaseModel):
    """Combined input for the Quality Checker node."""

    textbook: RawTextbook
    plan: CurriculumPlan


class QualityCheckerNode(PipelineNode[QualityCheckerInput, QualityReport]):
    """Node 6: Validates completeness, consistency, and difficulty progression."""

    input_schema = QualityCheckerInput
    output_schema = QualityReport

    async def run(self, input_data: QualityCheckerInput) -> QualityReport:
        raise NotImplementedError
