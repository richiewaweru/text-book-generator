from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.curriculum_plan import CurriculumPlan
from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.services.quality_checker import (
    QualityCheckerNode,
    QualityCheckerInput,
)


class CheckQualityUseCase:
    """Runs the quality checker on a generated textbook."""

    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider

    async def execute(
        self, textbook: RawTextbook, plan: CurriculumPlan
    ) -> QualityReport:
        node = QualityCheckerNode(provider=self.provider)
        return await node.execute(QualityCheckerInput(textbook=textbook, plan=plan))
