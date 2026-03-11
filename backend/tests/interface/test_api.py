from fastapi.testclient import TestClient

from textbook_agent.interface.api.app import app


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
    def test_generate_returns_501(self):
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
        assert response.status_code == 501

    def test_status_returns_501(self):
        response = client.get("/api/v1/status/some-id")
        assert response.status_code == 501
