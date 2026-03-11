from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from textbook_agent import __version__
from textbook_agent.infrastructure.config.settings import settings
from textbook_agent.infrastructure.database.models import Base
from textbook_agent.infrastructure.database.session import engine

from .routes.auth import router as auth_router
from .routes.generation import router as generation_router
from .routes.health import router as health_router
from .routes.profile import router as profile_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    if settings.frontend_origin != "http://localhost:5173":
        allowed_origins.append("http://localhost:5173")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(generation_router)

    return app


app = create_app()
