import sys
import asyncio
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from textbook_agent.interface.api.app import app
from conftest import MockProvider


client = TestClient(app)


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
            from textbook_agent.infrastructure.repositories.file_textbook_repo import (
                FileTextbookRepository,
            )
            from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer

            provider = MockProvider()
            repo = FileTextbookRepository(output_dir="outputs/")
            mock_uc.return_value = GenerateTextbookUseCase(
                provider=provider, repository=repo, renderer=HTMLRenderer()
            )

            response = client.post(
                "/api/v1/generate",
                json={
                    "subject": "algebra",
                    "age": 14,
                    "context": "test",
                    "depth": "survey",
                    "language": "plain",
                },
            )
            assert response.status_code == 202
            data = response.json()
            assert "generation_id" in data
            assert data["status"] == "pending"

    def test_status_unknown_returns_404(self):
        response = client.get("/api/v1/status/nonexistent-id")
        assert response.status_code == 404

    async def test_generate_and_poll_status(self):
        with patch(
            "textbook_agent.interface.api.routes.generation.get_use_case"
        ) as mock_uc:
            from textbook_agent.application.use_cases.generate_textbook import (
                GenerateTextbookUseCase,
            )
            from textbook_agent.infrastructure.repositories.file_textbook_repo import (
                FileTextbookRepository,
            )
            from textbook_agent.infrastructure.renderer.html_renderer import HTMLRenderer

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
                        "age": 14,
                        "context": "test",
                        "depth": "survey",
                        "language": "plain",
                    },
                )
                assert post_resp.status_code == 202
                gen_id = post_resp.json()["generation_id"]

                for _ in range(50):
                    status_resp = await ac.get(f"/api/v1/status/{gen_id}")
                    assert status_resp.status_code == 200
                    status_data = status_resp.json()
                    if status_data["status"] in ("completed", "failed"):
                        break
                    await asyncio.sleep(0.1)

                assert status_data["status"] == "completed"
                assert status_data["result"]["textbook_id"]
