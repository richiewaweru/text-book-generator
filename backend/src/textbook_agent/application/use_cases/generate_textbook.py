from collections.abc import Callable

from textbook_agent.application.dtos.generation_request import (
    GenerationRequest,
    GenerationResponse,
)
from textbook_agent.application.orchestrator import TextbookAgent
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.domain.ports.textbook_repository import TextbookRepository


class GenerateTextbookUseCase:
    """Orchestrates the full textbook generation pipeline."""

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
        renderer: RendererPort,
        quality_check_enabled: bool = True,
        max_quality_reruns: int = 2,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.renderer = renderer
        self.quality_check_enabled = quality_check_enabled
        self.max_quality_reruns = max_quality_reruns

    async def execute(
        self,
        request: GenerationRequest,
        student_profile: StudentProfile | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> GenerationResponse:
        ctx = self._build_generation_context(request, student_profile)
        agent = TextbookAgent(
            provider=self.provider,
            repository=self.repository,
            renderer=self.renderer,
            quality_check_enabled=self.quality_check_enabled,
            max_quality_reruns=self.max_quality_reruns,
            on_progress=on_progress,
        )
        return await agent.generate(ctx)

    @staticmethod
    def _build_generation_context(
        request: GenerationRequest,
        student_profile: StudentProfile | None,
    ) -> GenerationContext:
        """Merge persistent StudentProfile with per-generation request."""
        if student_profile is not None:
            return GenerationContext(
                subject=request.subject,
                age=student_profile.age,
                context=request.context,
                depth=request.depth or student_profile.preferred_depth,
                language=request.language or student_profile.preferred_notation,
                education_level=student_profile.education_level,
                interests=student_profile.interests,
                learning_style=student_profile.learning_style,
                goals=student_profile.goals,
                prior_knowledge=student_profile.prior_knowledge,
                learner_description=student_profile.learner_description,
            )
        return GenerationContext(
            subject=request.subject,
            age=16,
            context=request.context,
            depth=request.depth or "standard",
            language=request.language or "plain",
        )
