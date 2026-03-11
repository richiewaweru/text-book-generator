from functools import lru_cache

from textbook_agent.infrastructure.config.settings import Settings
from textbook_agent.infrastructure.providers.factory import ProviderFactory
from textbook_agent.infrastructure.repositories.file_textbook_repo import (
    FileTextbookRepository,
)
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.application.use_cases.generate_textbook import GenerateTextbookUseCase


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_provider(settings: Settings | None = None) -> BaseProvider:
    s = settings or get_settings()
    api_key = s.anthropic_api_key if s.provider == "claude" else s.openai_api_key
    model = s.claude_model if s.provider == "claude" else s.openai_model
    return ProviderFactory.get(s.provider, api_key=api_key, model=model)


def get_repository(settings: Settings | None = None) -> TextbookRepository:
    s = settings or get_settings()
    return FileTextbookRepository(output_dir=s.output_dir)


def get_renderer() -> RendererPort:
    return HTMLRenderer()


def get_use_case() -> GenerateTextbookUseCase:
    s = get_settings()
    return GenerateTextbookUseCase(
        provider=get_provider(s),
        repository=get_repository(s),
        renderer=get_renderer(),
        quality_check_enabled=s.quality_check_enabled,
    )
