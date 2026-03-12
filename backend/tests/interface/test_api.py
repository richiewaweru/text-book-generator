import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.domain.entities.user import User
from textbook_agent.interface.api.app import app
from textbook_agent.interface.api.dependencies import (
    get_generation_repository,
    get_jwt_handler,
    get_student_profile_repository,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user
from conftest import MockProvider

_TEST_USER = User(
    id="test-user-id",
    email="test@example.com",
    name="Test User",
    picture_url=None,
    has_profile=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)


async def _override_current_user():
    return _TEST_USER


class _MockProfileRepo:
    async def find_by_user_id(self, user_id: str):
        return None

    async def create(self, profile):
        return profile

    async def update(self, profile):
        return profile


async def _override_profile_repo():
    return _MockProfileRepo()


class _MockGenerationRepo:
    def __init__(self):
        self._store: dict = {}

    async def create(self, generation):
        self._store[generation.id] = generation
        return generation

    async def update_status(self, generation_id, status, **kwargs):
        if generation_id in self._store:
            gen = self._store[generation_id]
            self._store[generation_id] = gen.model_copy(
                update={"status": status, **{k: v for k, v in kwargs.items() if v is not None}}
            )

    async def find_by_id(self, generation_id):
        return self._store.get(generation_id)

    async def list_by_user(self, user_id, limit=20, offset=0):
        gens = [g for g in self._store.values() if g.user_id == user_id]
        gens.sort(key=lambda g: g.created_at, reverse=True)
        return gens[offset : offset + limit]


_mock_gen_repo = _MockGenerationRepo()


async def _override_gen_repo():
    return _mock_gen_repo


app.dependency_overrides[get_current_user] = _override_current_user
app.dependency_overrides[get_student_profile_repository] = _override_profile_repo
app.dependency_overrides[get_generation_repository] = _override_gen_repo

client = TestClient(app)

jwt_handler = get_jwt_handler()
_TEST_TOKEN = jwt_handler.create_access_token(_TEST_USER.id, _TEST_USER.email)
AUTH_HEADERS = {"Authorization": f"Bearer {_TEST_TOKEN}"}


class TestHealthCheck:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_version_matches(self):
        from textbook_agent import __version__

        response = client.get("/health")
        assert response.json()["version"] == __version__


class TestGenerationEndpoints:
    def test_generate_returns_202(self):
        with patch(
            "textbook_agent.interface.api.routes.generation.get_use_case"
        ) as mock_uc:
            from textbook_agent.application.use_cases.generate_textbook import (
                GenerateTextbookUseCase,
            )
            from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
            from textbook_agent.infrastructure.repositories.file_textbook_repo import (
                FileTextbookRepository,
            )

            provider = MockProvider()
            repo = FileTextbookRepository(output_dir="outputs/")
            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider, repository=repo, renderer=HTMLRenderer()
            )

            response = client.post(
                "/api/v1/generate",
                json={
                    "subject": "algebra",
                    "context": "test",
                    "depth": "survey",
                },
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 202
            data = response.json()
            assert "generation_id" in data
            assert data["status"] == "pending"

    def test_generate_returns_401_without_auth(self):
        app.dependency_overrides.pop(get_current_user, None)
        try:
            response = client.post(
                "/api/v1/generate",
                json={"subject": "algebra", "context": "test"},
            )
            assert response.status_code in (401, 403)
        finally:
            app.dependency_overrides[get_current_user] = _override_current_user

    def test_status_unknown_returns_404(self):
        response = client.get("/api/v1/status/nonexistent-id", headers=AUTH_HEADERS)
        assert response.status_code == 404

    async def test_generate_and_poll_status(self):
        with patch(
            "textbook_agent.interface.api.routes.generation.get_use_case"
        ) as mock_uc:
            from textbook_agent.application.use_cases.generate_textbook import (
                GenerateTextbookUseCase,
            )
            from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
            from textbook_agent.infrastructure.repositories.file_textbook_repo import (
                FileTextbookRepository,
            )

            provider = MockProvider()
            repo = FileTextbookRepository(output_dir="outputs/")
            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider, repository=repo, renderer=HTMLRenderer()
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                post_resp = await ac.post(
                    "/api/v1/generate",
                    json={
                        "subject": "algebra",
                        "context": "test",
                        "depth": "survey",
                    },
                    headers=AUTH_HEADERS,
                )
                assert post_resp.status_code == 202
                gen_id = post_resp.json()["generation_id"]

                for _ in range(50):
                    status_resp = await ac.get(
                        f"/api/v1/status/{gen_id}", headers=AUTH_HEADERS
                    )
                    assert status_resp.status_code == 200
                    status_data = status_resp.json()
                    if status_data["status"] in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.1)

                assert status_data["status"] == "completed"
                assert status_data["result"]["textbook_id"]

    async def test_list_generations(self):
        with patch(
            "textbook_agent.interface.api.routes.generation.get_use_case"
        ) as mock_uc:
            from textbook_agent.application.use_cases.generate_textbook import (
                GenerateTextbookUseCase,
            )
            from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer
            from textbook_agent.infrastructure.repositories.file_textbook_repo import (
                FileTextbookRepository,
            )

            provider = MockProvider()
            repo = FileTextbookRepository(output_dir="outputs/")
            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider, repository=repo, renderer=HTMLRenderer()
            )

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                post_resp = await ac.post(
                    "/api/v1/generate",
                    json={"subject": "calculus", "context": "test"},
                    headers=AUTH_HEADERS,
                )
                assert post_resp.status_code == 202
                gen_id = post_resp.json()["generation_id"]

                list_resp = await ac.get(
                    "/api/v1/generations", headers=AUTH_HEADERS
                )
                assert list_resp.status_code == 200
                items = list_resp.json()
                gen_ids = [item["id"] for item in items]
                assert gen_id in gen_ids


class TestErrorHandler:
    def test_structured_error_responses(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient as TC

        from textbook_agent.domain.exceptions import PipelineError, ProviderConformanceError
        from textbook_agent.interface.api.middleware.error_handler import register_error_handlers

        test_app_local = FastAPI()
        register_error_handlers(test_app_local)

        @test_app_local.get("/test-pipeline-error")
        async def trigger_pipeline_error():
            raise PipelineError(node_name="ContentGenerator", reason="LLM timeout")

        @test_app_local.get("/test-provider-error")
        async def trigger_provider_error():
            raise ProviderConformanceError(
                provider_name="claude", schema_name="SectionContent"
            )

        tc = TC(test_app_local)

        resp = tc.get("/test-pipeline-error")
        assert resp.status_code == 502
        data = resp.json()
        assert data["error_type"] == "pipeline_error"
        assert "ContentGenerator" in data["detail"]

        resp = tc.get("/test-provider-error")
        assert resp.status_code == 502
        data = resp.json()
        assert data["error_type"] == "provider_error"
        assert "claude" in data["detail"]
