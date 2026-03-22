from datetime import datetime, timezone
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.user import User
from textbook_agent.interface.api import app as app_module
from textbook_agent.interface.api.app import create_app
from textbook_agent.interface.api.dependencies import (
    get_generation_repository,
    get_jwt_handler,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user


TEST_USER = User(
    id="runtime-test-user",
    email="runtime@example.com",
    name="Runtime Test",
    picture_url=None,
    has_profile=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)


async def _override_current_user():
    return TEST_USER


class _StubGenerationRepo:
    def __init__(self, items: dict[str, Generation] | None = None):
        self._items = items or {}

    async def create(self, generation: Generation):
        self._items[generation.id] = generation
        return generation

    async def update_status(self, generation_id, status, **kwargs):
        generation = self._items[generation_id]
        updates = {"status": status}
        updates.update({key: value for key, value in kwargs.items() if value is not None})
        self._items[generation_id] = generation.model_copy(update=updates)

    async def find_by_id(self, generation_id: str):
        return self._items.get(generation_id)

    async def list_by_user(self, user_id: str, limit: int = 20, offset: int = 0):
        results = [item for item in self._items.values() if item.user_id == user_id]
        results.sort(key=lambda item: item.created_at, reverse=True)
        return results[offset : offset + limit]


def _auth_headers() -> dict[str, str]:
    jwt_handler = get_jwt_handler()
    token = jwt_handler.create_access_token(TEST_USER.id, TEST_USER.email)
    return {"Authorization": f"Bearer {token}"}


class TestRuntimeDiagnostics:
    def test_health_exposes_runtime_fingerprint(self):
        with TestClient(create_app()) as client:
            response = client.get("/health")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["instance_id"]
        assert payload["started_at"]
        assert payload["pipeline_architecture"] == "shell-pipeline-native-lectio"

    async def test_history_and_detail_expose_error_metadata(self):
        generation = Generation(
            id="pipeline-failure",
            user_id=TEST_USER.id,
            subject="history",
            context="",
            status="failed",
            mode="draft",
            error="pipeline failure",
            error_type="pipeline_error",
            error_code="pipeline_failed",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            created_at=datetime.now(timezone.utc),
        )
        repo = _StubGenerationRepo({generation.id: generation})
        app = create_app()
        app.dependency_overrides[get_current_user] = _override_current_user
        app.dependency_overrides[get_generation_repository] = lambda: repo

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                list_response = await ac.get("/api/v1/generations", headers=_auth_headers())
                detail_response = await ac.get(
                    f"/api/v1/generations/{generation.id}",
                    headers=_auth_headers(),
                )
        finally:
            app.dependency_overrides.clear()

        assert list_response.status_code == 200
        assert list_response.json()[0]["error_type"] == "pipeline_error"
        assert detail_response.status_code == 200
        assert detail_response.json()["error_code"] == "pipeline_failed"

    async def test_reset_legacy_generation_table_recreates_document_schema(self, tmp_path):
        db_path = tmp_path / "runtime-reset.db"
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        original_engine = app_module.engine

        try:
            app_module.engine = test_engine
            async with test_engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE generations (
                            id VARCHAR PRIMARY KEY,
                            user_id VARCHAR NOT NULL,
                            subject VARCHAR NOT NULL,
                            context TEXT,
                            mode VARCHAR,
                            status VARCHAR,
                            output_path VARCHAR,
                            requested_display_mode VARCHAR
                        )
                        """
                    )
                )

            reset = await app_module._reset_legacy_generation_table_if_needed()
            assert reset is True

            async with test_engine.begin() as conn:
                result = await conn.execute(text("PRAGMA table_info(generations)"))
                columns = {row[1] for row in result.fetchall()}
        finally:
            app_module.engine = original_engine
            await test_engine.dispose()

        assert "document_path" in columns
        assert "requested_preset_id" in columns
        assert "output_path" not in columns

    async def test_reset_legacy_generation_table_noops_when_schema_is_current(self, tmp_path):
        db_path = tmp_path / "runtime-current.db"
        test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        original_engine = app_module.engine

        try:
            app_module.engine = test_engine
            async with test_engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        CREATE TABLE generations (
                            id VARCHAR PRIMARY KEY,
                            user_id VARCHAR NOT NULL,
                            subject VARCHAR NOT NULL,
                            context TEXT,
                            mode VARCHAR,
                            status VARCHAR,
                            document_path VARCHAR,
                            error TEXT,
                            error_type VARCHAR,
                            error_code VARCHAR,
                            requested_template_id VARCHAR,
                            resolved_template_id VARCHAR,
                            requested_preset_id VARCHAR,
                            resolved_preset_id VARCHAR,
                            section_count INTEGER,
                            quality_passed BOOLEAN,
                            generation_time_seconds FLOAT,
                            source_generation_id VARCHAR,
                            created_at DATETIME NOT NULL,
                            completed_at DATETIME
                        )
                        """
                    )
                )

            reset = await app_module._reset_legacy_generation_table_if_needed()
        finally:
            app_module.engine = original_engine
            await test_engine.dispose()

        assert reset is False
