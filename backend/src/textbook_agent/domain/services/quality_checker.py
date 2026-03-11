import asyncio

from pydantic import BaseModel

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.prompts.quality_prompts import build_quality_prompt
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
        prompt = build_quality_prompt(input_data.textbook, input_data.plan)
        return await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt="Review this textbook for quality issues.",
            response_schema=QualityReport,
        )
