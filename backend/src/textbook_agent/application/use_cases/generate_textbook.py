from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.application.dtos.generation_request import (
    GenerationRequest,
    GenerationResponse,
)


class GenerateTextbookUseCase:
    """Orchestrates the full textbook generation pipeline."""

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
    ) -> None:
        self.provider = provider
        self.repository = repository

    async def execute(self, request: GenerationRequest) -> GenerationResponse:
        raise NotImplementedError
