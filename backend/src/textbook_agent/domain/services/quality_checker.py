import asyncio

from pydantic import BaseModel

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.prompts.quality_prompts import build_quality_prompt

from .quality_rules import run_mechanical_checks
from .severity_policy import apply_severity_policy
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
        mechanical_issues = run_mechanical_checks(
            textbook=input_data.textbook,
            plan=input_data.plan,
        )
        prompt = build_quality_prompt(input_data.textbook, input_data.plan)
        llm_report = await asyncio.to_thread(
            self.provider.complete,
            system_prompt=prompt,
            user_prompt="Review this textbook for quality issues.",
            response_schema=QualityReport,
        )
        llm_issues = [
            issue.model_copy(update={"check_source": "llm"})
            for issue in llm_report.issues
        ]
        llm_issues = apply_severity_policy(llm_issues)
        merged_issues = [*mechanical_issues, *llm_issues]
        return QualityReport(
            passed=not any(issue.severity == "error" for issue in merged_issues),
            issues=merged_issues,
        )
