import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.domain.entities.user import User
from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.interface.api.app import app
from textbook_agent.interface.api.dependencies import (
    get_generation_repository,
    get_jwt_handler,
    get_student_profile_repository,
    get_textbook_repository,
    get_user_repository,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user
from textbook_agent.domain.value_objects import GenerationMode
from conftest import (
    MockProvider,
    SAMPLE_CODE,
    SAMPLE_CONTENT,
    SAMPLE_DIAGRAM,
    SAMPLE_PLAN,
)

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


class _AuthProfileRepo:
    def __init__(self):
        self._profiles: dict = {}

    async def find_by_user_id(self, user_id: str):
        return self._profiles.get(user_id)

    async def create(self, profile):
        self._profiles[profile.user_id] = profile
        return profile

    async def update(self, profile):
        self._profiles[profile.user_id] = profile
        return profile


class _AuthUserRepo:
    def __init__(self, user: User, profile_repo: _AuthProfileRepo):
        self._users = {user.id: user.model_copy(update={"has_profile": False})}
        self._profile_repo = profile_repo

    async def find_by_email(self, email: str):
        for user in self._users.values():
            if user.email == email:
                profile = await self._profile_repo.find_by_user_id(user.id)
                return user.model_copy(update={"has_profile": profile is not None})
        return None

    async def find_by_id(self, user_id: str):
        user = self._users.get(user_id)
        if user is None:
            return None
        profile = await self._profile_repo.find_by_user_id(user_id)
        return user.model_copy(update={"has_profile": profile is not None})

    async def create(self, user: User):
        self._users[user.id] = user
        return user

    async def update(self, user: User):
        self._users[user.id] = user
        return user


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


class TestAuthEndpoints:
    async def test_auth_me_returns_user_for_valid_jwt(self):
        profile_repo = _AuthProfileRepo()
        user_repo = _AuthUserRepo(_TEST_USER, profile_repo)

        async def _override_auth_user_repo():
            return user_repo

        async def _override_auth_profile_repo():
            return profile_repo

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_user_repository] = _override_auth_user_repo
        app.dependency_overrides[get_student_profile_repository] = (
            _override_auth_profile_repo
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get("/api/v1/auth/me", headers=AUTH_HEADERS)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == _TEST_USER.id
            assert data["has_profile"] is False
        finally:
            app.dependency_overrides[get_current_user] = _override_current_user
            app.dependency_overrides.pop(get_user_repository, None)
            app.dependency_overrides[get_student_profile_repository] = (
                _override_profile_repo
            )

    async def test_auth_me_returns_401_for_invalid_jwt(self):
        profile_repo = _AuthProfileRepo()
        user_repo = _AuthUserRepo(_TEST_USER, profile_repo)

        async def _override_auth_user_repo():
            return user_repo

        async def _override_auth_profile_repo():
            return profile_repo

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_user_repository] = _override_auth_user_repo
        app.dependency_overrides[get_student_profile_repository] = (
            _override_auth_profile_repo
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": "Bearer invalid-token"},
                )
            assert response.status_code == 401
        finally:
            app.dependency_overrides[get_current_user] = _override_current_user
            app.dependency_overrides.pop(get_user_repository, None)
            app.dependency_overrides[get_student_profile_repository] = (
                _override_profile_repo
            )

    async def test_auth_me_reflects_profile_creation(self):
        profile_repo = _AuthProfileRepo()
        user_repo = _AuthUserRepo(_TEST_USER, profile_repo)

        async def _override_auth_user_repo():
            return user_repo

        async def _override_auth_profile_repo():
            return profile_repo

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides[get_user_repository] = _override_auth_user_repo
        app.dependency_overrides[get_student_profile_repository] = (
            _override_auth_profile_repo
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                create_response = await ac.post(
                    "/api/v1/profile",
                    json={
                        "age": 18,
                        "education_level": "high_school",
                        "interests": ["math"],
                        "learning_style": "reading_writing",
                        "preferred_notation": "plain",
                        "prior_knowledge": "",
                        "goals": "",
                        "preferred_depth": "standard",
                        "learner_description": "",
                    },
                    headers=AUTH_HEADERS,
                )
                assert create_response.status_code == 201

                auth_response = await ac.get("/api/v1/auth/me", headers=AUTH_HEADERS)
            assert auth_response.status_code == 200
            assert auth_response.json()["has_profile"] is True
        finally:
            app.dependency_overrides[get_current_user] = _override_current_user
            app.dependency_overrides.pop(get_user_repository, None)
            app.dependency_overrides[get_student_profile_repository] = (
                _override_profile_repo
            )


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
            assert data["mode"] == "draft"

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
                assert all("output_path" not in item for item in items)

    async def test_get_generation_textbook_html(self, tmp_path):
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
            repo = FileTextbookRepository(output_dir=str(tmp_path))
            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider, repository=repo, renderer=HTMLRenderer()
            )
            app.dependency_overrides[get_textbook_repository] = lambda: repo

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    post_resp = await ac.post(
                        "/api/v1/generate",
                        json={"subject": "calculus", "context": "test"},
                        headers=AUTH_HEADERS,
                    )
                    assert post_resp.status_code == 202
                    gen_id = post_resp.json()["generation_id"]

                    for _ in range(50):
                        status_resp = await ac.get(
                            f"/api/v1/status/{gen_id}", headers=AUTH_HEADERS
                        )
                        status_data = status_resp.json()
                        if status_data["status"] in ("completed", "failed"):
                            break
                        await asyncio.sleep(0.1)

                    html_resp = await ac.get(
                        f"/api/v1/generations/{gen_id}/textbook",
                        headers=AUTH_HEADERS,
                    )
                    assert html_resp.status_code == 200
                    assert "<!DOCTYPE html>" in html_resp.text
            finally:
                app.dependency_overrides.pop(get_textbook_repository, None)

    async def test_get_generation_textbook_returns_409_when_not_ready(self):
        gen_id = "pending-textbook"
        _mock_gen_repo._store[gen_id] = Generation(
            id=gen_id,
            user_id=_TEST_USER.id,
            subject="algebra",
            status="running",
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get(
                    f"/api/v1/generations/{gen_id}/textbook",
                    headers=AUTH_HEADERS,
                )
            assert resp.status_code == 409
        finally:
            _mock_gen_repo._store.pop(gen_id, None)

    async def test_get_generation_textbook_rejects_foreign_generation(self):
        gen_id = "foreign-textbook"
        _mock_gen_repo._store[gen_id] = Generation(
            id=gen_id,
            user_id="other-user",
            subject="algebra",
            status="completed",
            output_path="other.html",
        )

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get(
                    f"/api/v1/generations/{gen_id}/textbook",
                    headers=AUTH_HEADERS,
                )
            assert resp.status_code == 404
        finally:
            _mock_gen_repo._store.pop(gen_id, None)

    async def test_generation_status_surfaces_provider_request_errors(self):
        from textbook_agent.domain.exceptions import ProviderRequestError

        class _FailingUseCase:
            async def execute(self, *args, **kwargs):
                raise ProviderRequestError(
                    provider_name="claude",
                    detail="Anthropic reports the API credit balance is too low.",
                )

        with patch(
            "textbook_agent.interface.api.routes.generation.get_use_case",
            return_value=_FailingUseCase(),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                post_resp = await ac.post(
                    "/api/v1/generate",
                    json={"subject": "calculus", "context": "test"},
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

                assert status_data["status"] == "failed"
                assert status_data["error_type"] == "provider_error"
                assert "credit balance is too low" in status_data["error"]

    async def test_enhance_draft_generation(self, beginner_profile, tmp_path):
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
            repo = FileTextbookRepository(output_dir=str(tmp_path))
            draft = RawTextbook(
                subject="algebra",
                profile=beginner_profile,
                plan=SAMPLE_PLAN,
                sections=[SAMPLE_CONTENT],
                diagrams=[SAMPLE_DIAGRAM],
                code_examples=[SAMPLE_CODE],
            )
            output_path = await repo.save(draft, "<!DOCTYPE html><html></html>")
            draft_generation_id = "draft-gen-1"
            child_generation_id: str | None = None
            _mock_gen_repo._store[draft_generation_id] = Generation(
                id=draft_generation_id,
                user_id=_TEST_USER.id,
                subject="algebra",
                context="test",
                status="completed",
                mode=GenerationMode.DRAFT,
                output_path=output_path,
            )

            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider,
                repository=repo,
                renderer=HTMLRenderer(),
            )
            app.dependency_overrides[get_textbook_repository] = lambda: repo

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    enhance_resp = await ac.post(
                        f"/api/v1/generations/{draft_generation_id}/enhance",
                        json={"target_mode": "balanced"},
                        headers=AUTH_HEADERS,
                    )
                    assert enhance_resp.status_code == 202
                    enhance_data = enhance_resp.json()
                    child_generation_id = enhance_data["generation_id"]
                    assert enhance_data["mode"] == "balanced"
                    assert enhance_data["source_generation_id"] == draft_generation_id

                    for _ in range(50):
                        status_resp = await ac.get(
                            f"/api/v1/status/{child_generation_id}",
                            headers=AUTH_HEADERS,
                        )
                        assert status_resp.status_code == 200
                        status_data = status_resp.json()
                        if status_data["status"] in ("completed", "failed"):
                            break
                        await asyncio.sleep(0.1)

                    assert status_data["status"] == "completed"
                    assert status_data["mode"] == "balanced"
                    assert status_data["source_generation_id"] == draft_generation_id
                    assert status_data["result"]["source_generation_id"] == draft_generation_id
                    assert status_data["result"]["mode"] == "balanced"
            finally:
                app.dependency_overrides.pop(get_textbook_repository, None)
                _mock_gen_repo._store.pop(draft_generation_id, None)
                if child_generation_id is not None:
                    _mock_gen_repo._store.pop(child_generation_id, None)


class TestErrorHandler:
    def test_structured_error_responses(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient as TC

        from textbook_agent.domain.exceptions import (
            PipelineError,
            ProviderConformanceError,
            ProviderRequestError,
        )
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

        @test_app_local.get("/test-provider-request-error")
        async def trigger_provider_request_error():
            raise ProviderRequestError(
                provider_name="claude",
                detail="Anthropic reports the API credit balance is too low.",
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

        resp = tc.get("/test-provider-request-error")
        assert resp.status_code == 502
        data = resp.json()
        assert data["error_type"] == "provider_error"
        assert "credit balance is too low" in data["detail"]
