from typing import Callable

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.application.dtos.generation_request import (
    GenerationRequest,
    GenerationResponse,
)
from textbook_agent.application.orchestrator import TextbookAgent


class GenerateTextbookUseCase:
    """Orchestrates the full textbook generation pipeline."""

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
        renderer: RendererPort,
        quality_check_enabled: bool = True,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.renderer = renderer
        self.quality_check_enabled = quality_check_enabled

    async def execute(
        self,
        request: GenerationRequest,
        on_progress: Callable[[str], None] | None = None,
    ) -> GenerationResponse:
        profile = LearnerProfile(
            subject=request.subject,
            age=request.age,
            context=request.context,
            depth=request.depth,
            language=request.language,
        )
        agent = TextbookAgent(
            provider=self.provider,
            repository=self.repository,
            renderer=self.renderer,
            quality_check_enabled=self.quality_check_enabled,
            on_progress=on_progress,
        )
        return await agent.generate(profile)
