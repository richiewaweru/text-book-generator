import asyncio
import inspect
import json
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.database.migrations import upgrade_database
from core.database.models import GenerationModel
from core.database.session import async_session_factory, engine
from core.errors import register_error_handlers
from core.routes.auth import router as auth_router
from core.routes.health import router as health_router
from core.routes.profile import router as profile_router
from core.routes.shares import router as shares_router
from generation.dependencies import get_document_repository, get_generation_repository
from generation.recovery import mark_stale_generations_failed
from generation.repositories.sql_document_repo import SqlDocumentRepository
from generation.repositories.sql_generation_repo import SqlGenerationRepository
from generation.routes import router as generation_router
from planning.routes import router as brief_router
from telemetry import telemetry_router
from telemetry.dependencies import get_llm_call_repository, get_report_repository
from telemetry.service import telemetry_monitor

logger = logging.getLogger("uvicorn.error")
__version__ = "0.1.0"
_STALE_HEARTBEAT_TIMEOUT = timedelta(minutes=2)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "generation_id",
            "user_id",
            "node",
            "latency_ms",
            "caller",
            "trace_id",
            "slot",
            "status_code",
            "timeout_seconds",
            "template_id",
            "preset_id",
            "section_count",
            "endpoint_host",
            "error",
            "instance_id",
            "started_at",
            "pipeline_architecture",
            "stale_generations",
            "telemetry_backfill",
        ):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    if settings.json_logging:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


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


async def _mark_stale_generations_failed() -> int:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - _STALE_HEARTBEAT_TIMEOUT
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationModel).where(
                GenerationModel.status.in_(("pending", "running")),
                or_(
                    GenerationModel.last_heartbeat.is_(None),
                    GenerationModel.last_heartbeat < cutoff,
                ),
            )
        )
        models = result.scalars().all()
        if not models:
            return 0

        generation_repository = SqlGenerationRepository(session)
        return await mark_stale_generations_failed(
            [SqlGenerationRepository._to_entity(model) for model in models],
            generation_repository=generation_repository,
            document_repository=SqlDocumentRepository(session),
            report_repository=None,
        )


async def _resolve_override(app: FastAPI, dependency):
    provider = app.dependency_overrides.get(dependency)
    if provider is None:
        return None

    value = provider()
    if inspect.isasyncgen(value):
        try:
            return await anext(value)
        finally:
            await value.aclose()
    if inspect.isawaitable(value):
        return await value
    return value


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def load_generation(generation_id: str):
        repository = await _resolve_override(app, get_generation_repository)
        if repository is None:
            return None
        return await repository.find_by_id(generation_id)

    async def load_document(document_path: str):
        repository = await _resolve_override(app, get_document_repository)
        if repository is None:
            return None
        return await repository.load_document(document_path)

    async def load_report_repository():
        return await _resolve_override(app, get_report_repository)

    async def load_llm_call_repository():
        return await _resolve_override(app, get_llm_call_repository)

    telemetry_monitor.configure(
        report_repository_factory=load_report_repository,
        llm_call_repository_factory=load_llm_call_repository,
        generation_loader=load_generation,
        document_loader=load_document,
    )
    if settings.run_migrations_on_startup:
        await asyncio.to_thread(upgrade_database)
    await telemetry_monitor.start()
    stale_generations = await _mark_stale_generations_failed()
    telemetry_backfill = await telemetry_monitor.backfill_failed_reports()
    app.state.instance_id = str(uuid4())
    app.state.started_at = datetime.now(timezone.utc)
    app.state.pipeline_architecture = "shell-pipeline-native-lectio"
    logger.info(
        "Runtime ready",
        extra={
            "instance_id": app.state.instance_id,
            "started_at": app.state.started_at.isoformat(),
            "pipeline_architecture": app.state.pipeline_architecture,
            "stale_generations": stale_generations,
            "telemetry_backfill": telemetry_backfill,
        },
    )
    yield
    await telemetry_monitor.stop()
    telemetry_monitor.configure()
    await engine.dispose()


def create_app() -> FastAPI:
    configure_logging()
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
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(SecurityHeadersMiddleware)

    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(shares_router)
    app.include_router(profile_router)
    app.include_router(brief_router)
    app.include_router(generation_router)
    app.include_router(telemetry_router)

    return app


app = create_app()
