from collections.abc import AsyncGenerator
from functools import lru_cache

from textbook_agent.domain.ports.document_repository import DocumentRepository
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.ports.user_repository import UserRepository
from textbook_agent.infrastructure.auth.jwt_handler import JWTHandler
from textbook_agent.infrastructure.config.settings import Settings
from textbook_agent.infrastructure.database.session import async_session_factory
from textbook_agent.infrastructure.repositories.file_document_repo import (
    FileDocumentRepository,
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
    settings = get_settings()
    return JWTHandler(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_access_token_expire_minutes,
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


@lru_cache
def get_document_repository() -> DocumentRepository:
    settings = get_settings()
    return FileDocumentRepository(output_dir=settings.document_output_dir)
