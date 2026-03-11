from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.application.dtos.generation_request import GenerationResponse


class TextbookAgent:
    """Top-level orchestrator that wires the 6-node pipeline together.

    Pipeline flow:
        LearnerProfile
        -> [1] Planner -> CurriculumPlan
        -> [2] ContentGenerator -> list[SectionContent]
        -> [3] DiagramGenerator -> list[SectionDiagram]
        -> [4] CodeGenerator -> list[SectionCode]
        -> [5] Assembler -> RawTextbook
        -> [6] QualityChecker -> QualityReport
        -> HTMLRenderer -> final output
    """

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
    ) -> None:
        self.provider = provider
        self.repository = repository

    async def generate(self, profile: LearnerProfile) -> GenerationResponse:
        raise NotImplementedError
