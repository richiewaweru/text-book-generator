import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from textbook_agent import __version__
from textbook_agent.infrastructure.config.settings import settings
from textbook_agent.infrastructure.database.models import Base, GenerationModel
from textbook_agent.infrastructure.database.session import async_session_factory, engine
from textbook_agent.infrastructure.repositories.sql_generation_repo import (
    SqlGenerationRepository,
)

from .dependencies import get_document_repository, get_report_repository
from .generation_recovery import mark_stale_generations_failed
from .middleware.error_handler import register_error_handlers
from .routes.auth import router as auth_router
from .routes.brief import router as brief_router
from .routes.generation import router as generation_router
from .routes.health import router as health_router
from .routes.profile import router as profile_router

logger = logging.getLogger("uvicorn.error")


def _allowed_frontend_origins(frontend_origin: str) -> list[str]:
    parsed = urlsplit(frontend_origin)
    hostname = parsed.hostname
    if hostname not in {"localhost", "127.0.0.1"}:
        return [frontend_origin]

    port_suffix = f":{parsed.port}" if parsed.port is not None else ""
    netloc_template = "{host}" + port_suffix
    variants = []
    for host in ("localhost", "127.0.0.1"):
        candidate = urlunsplit(
            (
                parsed.scheme,
                netloc_template.format(host=host),
                parsed.path,
                parsed.query,
                parsed.fragment,
            )
        )
        if candidate not in variants:
            variants.append(candidate)
    return variants


async def _reset_legacy_generation_table_if_needed() -> bool:
    async with engine.begin() as conn:
        if conn.dialect.name != "sqlite":
            return False

        exists = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='generations'"
            )
        )
        if exists.scalar_one_or_none() is None:
            return False

        result = await conn.execute(text("PRAGMA table_info(generations)"))
        existing = {row[1] for row in result.fetchall()}
        expected = {
            "id",
            "user_id",
            "subject",
            "context",
            "mode",
            "status",
            "document_path",
            "error",
            "error_type",
            "error_code",
            "requested_template_id",
            "resolved_template_id",
            "requested_preset_id",
            "resolved_preset_id",
            "section_count",
            "quality_passed",
            "generation_time_seconds",
            "source_generation_id",
            "planning_spec_json",
            "created_at",
            "completed_at",
        }
        legacy_markers = {
            "output_path",
            "requested_display_mode",
            "resolved_display_mode",
            "resolved_template_name",
        }
        if existing == expected:
            return False
        if expected - existing:
            await conn.run_sync(
                lambda sync_conn: GenerationModel.__table__.drop(sync_conn, checkfirst=True)
            )
            await conn.run_sync(
                lambda sync_conn: GenerationModel.__table__.create(sync_conn, checkfirst=True)
            )
            return True
        if not (legacy_markers & existing or "document_path" not in existing):
            return False

        await conn.run_sync(
            lambda sync_conn: GenerationModel.__table__.drop(sync_conn, checkfirst=True)
        )
        await conn.run_sync(
            lambda sync_conn: GenerationModel.__table__.create(sync_conn, checkfirst=True)
        )
        return True


async def _mark_stale_generations_failed() -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationModel).where(
                GenerationModel.status.in_(("pending", "running"))
            )
        )
        models = result.scalars().all()
        if not models:
            return 0

        generation_repository = SqlGenerationRepository(session)
        return await mark_stale_generations_failed(
            [SqlGenerationRepository._to_entity(model) for model in models],
            generation_repository=generation_repository,
            document_repository=get_document_repository(),
            report_repository=get_report_repository(),
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    reset_generations = await _reset_legacy_generation_table_if_needed()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    stale_generations = await _mark_stale_generations_failed()
    app.state.instance_id = str(uuid4())
    app.state.started_at = datetime.now(timezone.utc)
    app.state.pipeline_architecture = "shell-pipeline-native-lectio"
    logger.info(
        "Runtime ready instance_id=%s started_at=%s pipeline_architecture=%s reset_generations=%s stale_generations=%s",
        app.state.instance_id,
        app.state.started_at.isoformat(),
        app.state.pipeline_architecture,
        reset_generations,
        stale_generations,
    )
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textbook Generation Agent",
        version=__version__,
        description="AI-agnostic pipeline for generating personalized textbooks",
        lifespan=lifespan,
    )

    allowed_origins = _allowed_frontend_origins(settings.frontend_origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(brief_router)
    app.include_router(generation_router)

    return app


app = create_app()
