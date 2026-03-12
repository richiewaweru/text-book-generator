from collections.abc import AsyncGenerator
from functools import lru_cache

from textbook_agent.application.use_cases.generate_textbook import GenerateTextbookUseCase
from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.ports.renderer import RendererPort
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.ports.user_repository import UserRepository
from textbook_agent.infrastructure.auth.jwt_handler import JWTHandler
from textbook_agent.infrastructure.config.settings import Settings
from textbook_agent.infrastructure.database.session import async_session_factory
from textbook_agent.infrastructure.providers.factory import ProviderFactory
from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
from textbook_agent.infrastructure.repositories.file_textbook_repo import (
    FileTextbookRepository,
)
from textbook_agent.infrastructure.repositories.sql_generation_repo import (
    SqlGenerationRepository,
)
from textbook_agent.infrastructure.repositories.sql_student_profile_repo import (
    SqlStudentProfileRepository,
)
from textbook_agent.infrastructure.repositories.sql_user_repo import SqlUserRepository


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_jwt_handler() -> JWTHandler:
    s = get_settings()
    return JWTHandler(
        secret_key=s.jwt_secret_key,
        algorithm=s.jwt_algorithm,
        expire_minutes=s.jwt_access_token_expire_minutes,
    )


async def get_user_repository() -> AsyncGenerator[UserRepository, None]:
    async with async_session_factory() as session:
        yield SqlUserRepository(session)


async def get_generation_repository() -> AsyncGenerator[GenerationRepository, None]:
    async with async_session_factory() as session:
        yield SqlGenerationRepository(session)


async def get_student_profile_repository() -> AsyncGenerator[StudentProfileRepository, None]:
    async with async_session_factory() as session:
        yield SqlStudentProfileRepository(session)


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
