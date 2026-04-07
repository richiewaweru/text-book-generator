from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app as app_module
from core.database.models import Base, GenerationModel


def test_cors_wildcard_raises_in_production() -> None:
    with pytest.raises(RuntimeError, match="FRONTEND_ORIGIN"):
        app_module._allowed_frontend_origins("*", env="production")


def test_cors_wildcard_allowed_in_development(monkeypatch) -> None:
    seen: list[str] = []

    def capture_warning(message: str, *args) -> None:
        seen.append(message % args if args else message)

    monkeypatch.setattr(app_module.logger, "warning", capture_warning)

    origins = app_module._allowed_frontend_origins("*", env="development")

    assert origins == ["*"]
    assert any("CORS is open" in message for message in seen)


def test_cors_multiple_origins_parsed() -> None:
    origins = app_module._allowed_frontend_origins(
        "https://app.vercel.app, https://preview.vercel.app",
        env="production",
    )

    assert origins == [
        "https://app.vercel.app",
        "https://preview.vercel.app",
    ]


def test_cors_localhost_origin_expands_to_local_variants() -> None:
    origins = app_module._allowed_frontend_origins(
        "http://localhost:5173",
        env="development",
    )

    assert origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_images_static_route_is_mounted() -> None:
    image_routes = [
        route for route in app_module.app.routes
        if getattr(route, "path", None) == "/images"
    ]

    assert image_routes, "Expected /images static mount to be registered"
    assert getattr(image_routes[0], "name", None) == "images"


@pytest.mark.asyncio
async def test_stale_generations_marked_failed_only_when_older_than_threshold(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "stale-cutoff.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr(app_module, "async_session_factory", session_factory)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stale_cutoff = now - timedelta(
        seconds=app_module.settings.pipeline_timeout_generation_cap_seconds
        + app_module._STALE_GENERATION_GRACE_SECONDS
    )

    async with session_factory() as session:
        session.add_all(
            [
                GenerationModel(
                    id="stale-old",
                    user_id="user-1",
                    subject="Algebra",
                    status="running",
                    created_at=stale_cutoff - timedelta(seconds=1),
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
                ),
                GenerationModel(
                    id="fresh-new",
                    user_id="user-1",
                    subject="Geometry",
                    status="running",
                    created_at=stale_cutoff + timedelta(seconds=1),
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
                ),
            ]
        )
        await session.commit()

    try:
        count = await app_module._mark_stale_generations_failed()

        assert count == 1

        async with session_factory() as session:
            result = await session.execute(
                select(GenerationModel).order_by(GenerationModel.id)
            )
            models = {model.id: model for model in result.scalars().all()}

        assert models["stale-old"].status == "failed"
        assert models["stale-old"].error_code == "worker_restart"
        assert models["fresh-new"].status == "running"
        assert models["fresh-new"].error is None
    finally:
        await engine.dispose()
