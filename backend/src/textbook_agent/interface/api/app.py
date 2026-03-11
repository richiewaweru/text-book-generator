from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from textbook_agent import __version__
from .routes.health import router as health_router
from .routes.generation import router as generation_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.jobs = {}
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Textbook Generation Agent",
        version=__version__,
        description="AI-agnostic pipeline for generating personalized textbooks",
        lifespan=lifespan,
    )

    app.state.jobs = {}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(generation_router)

    return app


app = create_app()
