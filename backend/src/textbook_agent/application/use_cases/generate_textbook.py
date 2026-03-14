from collections.abc import Callable

from textbook_agent.application.dtos.generation_request import (
    EnhanceGenerationRequest,
    GenerationRequest,
    GenerationResponse,
)
from textbook_agent.application.orchestrator import TextbookAgent
from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.value_objects import Depth, GenerationMode, ModelRouting


class GenerateTextbookUseCase:
    """Orchestrates the full textbook generation pipeline."""

    def __init__(
        self,
        provider: BaseProvider,
        repository: TextbookRepository,
        renderer: RendererPort,
        quality_check_enabled: bool = True,
        max_quality_reruns: int = 2,
        max_retries: int = 2,
        retry_base_delay: float = 1.0,
        code_line_soft_limit: int = 80,
        code_line_hard_limit: int = 300,
        model_routing: ModelRouting | None = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.renderer = renderer
        self.quality_check_enabled = quality_check_enabled
        self.max_quality_reruns = max_quality_reruns
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.code_line_soft_limit = code_line_soft_limit
        self.code_line_hard_limit = code_line_hard_limit
        self.model_routing = model_routing or ModelRouting()

    async def execute(
        self,
        request: GenerationRequest,
        student_profile: StudentProfile | None = None,
        on_progress: Callable | None = None,
    ) -> GenerationResponse:
        mode = request.resolved_mode()
        ctx = self._build_generation_context(request, student_profile, mode)
        agent = TextbookAgent(
            provider=self.provider,
            repository=self.repository,
            renderer=self.renderer,
            mode=mode,
            quality_check_enabled=self.quality_check_enabled,
            max_quality_reruns=self.max_quality_reruns,
            max_retries=self.max_retries,
            retry_base_delay=self.retry_base_delay,
            code_line_soft_limit=self.code_line_soft_limit,
            code_line_hard_limit=self.code_line_hard_limit,
            model_routing=self.model_routing,
            on_progress=on_progress,
        )
        return await agent.generate(ctx)

    async def enhance(
        self,
        request: EnhanceGenerationRequest,
        source_textbook: RawTextbook,
        on_progress: Callable | None = None,
        source_generation_id: str | None = None,
    ) -> GenerationResponse:
        if request.target_mode == GenerationMode.DRAFT:
            raise ValueError("Enhancement target_mode must be balanced or strict.")

        profile = source_textbook.profile
        if request.note.strip():
            profile = profile.model_copy(
                update={
                    "context": (
                        f"{profile.context}\nEnhancement note: {request.note.strip()}"
                    ).strip()
                }
            )

        agent = TextbookAgent(
            provider=self.provider,
            repository=self.repository,
            renderer=self.renderer,
            mode=request.target_mode,
            quality_check_enabled=self.quality_check_enabled,
            max_quality_reruns=self.max_quality_reruns,
            max_retries=self.max_retries,
            retry_base_delay=self.retry_base_delay,
            code_line_soft_limit=self.code_line_soft_limit,
            code_line_hard_limit=self.code_line_hard_limit,
            model_routing=self.model_routing,
            on_progress=on_progress,
        )
        return await agent.generate(
            profile,
            seed_textbook=source_textbook,
            source_generation_id=source_generation_id,
        )

    @staticmethod
    def _build_generation_context(
        request: GenerationRequest,
        student_profile: StudentProfile | None,
        mode: GenerationMode,
    ) -> GenerationContext:
        """Merge persistent StudentProfile with per-generation request."""
        resolved_depth = request.depth
        if mode == GenerationMode.DRAFT:
            resolved_depth = Depth.SURVEY

        if student_profile is not None:
            return GenerationContext(
                subject=request.subject,
                age=student_profile.age,
                context=request.context,
                depth=resolved_depth or student_profile.preferred_depth,
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
            depth=resolved_depth or "standard",
            language=request.language or "plain",
        )
