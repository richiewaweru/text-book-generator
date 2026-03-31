from datetime import datetime, timezone
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from core.entities.user import User
from core.dependencies import get_jwt_handler
from generation.entities.generation import Generation
import app as app_module
from app import create_app
from core.auth.middleware import get_current_user
from generation.dependencies import get_generation_repository


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

    async def count_active_by_user(self, user_id: str) -> int:
        return sum(
            1
            for item in self._items.values()
            if item.user_id == user_id and item.status in {"pending", "running"}
        )

    async def update_heartbeat(self, generation_id: str, heartbeat_at=None):
        generation = self._items[generation_id]
        self._items[generation_id] = generation.model_copy(
            update={"last_heartbeat": heartbeat_at or datetime.now(timezone.utc)}
        )


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

    def test_startup_runs_database_migrations_before_serving(self, monkeypatch):
        calls: list[str] = []

        def _upgrade_database() -> None:
            calls.append("upgrade")

        async def _mark_stale_generations_failed() -> int:
            return 0

        monkeypatch.setattr(app_module, "upgrade_database", _upgrade_database)
        monkeypatch.setattr(app_module, "_mark_stale_generations_failed", _mark_stale_generations_failed)

        with TestClient(create_app()) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert calls == ["upgrade"]

    async def test_history_and_detail_expose_error_metadata(self):
        generation = Generation(
            id="pipeline-failure",
            user_id=TEST_USER.id,
            subject="history",
            context="",
            status="failed",
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


