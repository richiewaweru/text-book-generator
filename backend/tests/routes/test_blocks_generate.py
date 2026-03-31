from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.entities.user import User

TEST_USER = User(
    id="block-gen-user",
    email="blocks@example.com",
    name="Blocks User",
    picture_url=None,
    has_profile=False,
    created_at="2026-03-28T00:00:00+00:00",
    updated_at="2026-03-28T00:00:00+00:00",
)


async def _override_user() -> User:
    return TEST_USER


@pytest.fixture(autouse=True)
def _reset_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_generate_block_returns_content_mocked_llm() -> None:
    app.dependency_overrides[get_current_user] = _override_user

    fake_content = {
        "headline": "Why plants matter",
        "body": "Plants convert light into chemical energy.",
        "anchor": "Energy",
        "type": "prose",
    }

    with patch(
        "generation.routes.run_block_generation",
        new=AsyncMock(return_value=fake_content),
    ):
        async with _client() as client:
            res = await client.post(
                "/api/v1/blocks/generate",
                json={
                    "component_id": "hook-hero",
                    "subject": "Biology",
                    "focus": "Photosynthesis intro",
                    "grade_band": "secondary",
                    "context_blocks": [],
                },
            )
    assert res.status_code == 200
    data = res.json()
    assert data["content"] == fake_content


@pytest.mark.asyncio
async def test_generate_block_requires_auth() -> None:
    async with _client() as client:
        res = await client.post(
            "/api/v1/blocks/generate",
            json={
                "component_id": "hook-hero",
                "subject": "Biology",
                "focus": "x",
                "grade_band": "secondary",
            },
        )
    assert res.status_code == 401
