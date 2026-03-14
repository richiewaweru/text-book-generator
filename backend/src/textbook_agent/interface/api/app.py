from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from textbook_agent import __version__
from textbook_agent.infrastructure.config.settings import settings
from textbook_agent.infrastructure.database.models import Base
from textbook_agent.infrastructure.database.session import engine

from .middleware.error_handler import register_error_handlers
from .routes.auth import router as auth_router
from .routes.generation import router as generation_router
from .routes.health import router as health_router
from .routes.profile import router as profile_router


async def _ensure_generation_columns() -> None:
    async with engine.begin() as conn:
        if conn.dialect.name != "sqlite":
            return
        result = await conn.execute(text("PRAGMA table_info(generations)"))
        existing = {row[1] for row in result.fetchall()}
        migrations = {
            "mode": "ALTER TABLE generations ADD COLUMN mode VARCHAR DEFAULT 'balanced'",
            "source_generation_id": "ALTER TABLE generations ADD COLUMN source_generation_id VARCHAR",
        }
        for column, statement in migrations.items():
            if column not in existing:
                await conn.execute(text(statement))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_generation_columns()
    app.state.jobs = {}
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textbook Generation Agent",
        version=__version__,
        description="AI-agnostic pipeline for generating personalized textbooks",
        lifespan=lifespan,
    )

    app.state.jobs = {}

    allowed_origins = [settings.frontend_origin]

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
    app.include_router(generation_router)

    return app


app = create_app()
