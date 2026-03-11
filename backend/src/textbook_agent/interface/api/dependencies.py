from functools import lru_cache

from textbook_agent.infrastructure.config.settings import Settings
from textbook_agent.infrastructure.providers.factory import ProviderFactory
from textbook_agent.infrastructure.repositories.file_textbook_repo import (
    FileTextbookRepository,
)
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.application.orchestrator import TextbookAgent


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_provider(settings: Settings | None = None) -> BaseProvider:
    s = settings or get_settings()
    return ProviderFactory.get(s.provider)


def get_repository(settings: Settings | None = None) -> TextbookRepository:
    s = settings or get_settings()
    return FileTextbookRepository(output_dir=s.output_dir)


def get_orchestrator() -> TextbookAgent:
    return TextbookAgent(
        provider=get_provider(),
        repository=get_repository(),
    )
