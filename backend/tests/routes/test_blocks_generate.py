from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.database.models import EditableLessonModel, UserModel
from core.database.session import get_async_session
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


async def _install_session_override(db_session_factory):
    async def override_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_async_session] = override_session


@pytest.mark.asyncio
async def test_generate_block_rejects_unowned_lesson(db_session_factory) -> None:
    app.dependency_overrides[get_current_user] = _override_user
    await _install_session_override(db_session_factory)

    async with db_session_factory() as session:
        session.add(UserModel(id=TEST_USER.id, email=TEST_USER.email, name=TEST_USER.name))
        session.add(UserModel(id="other-user", email="other@example.com", name="Other User"))
        session.add(
            EditableLessonModel(
                id="lesson-owned-by-other",
                user_id="other-user",
                source_type="manual",
                title="Other lesson",
                document_json={
                    "version": 1,
                    "id": "lesson-owned-by-other",
                    "title": "Other lesson",
                    "subject": "science",
                    "preset_id": "blue-classroom",
                    "source": "manual",
                    "sections": [],
                    "blocks": {},
                    "media": {},
                    "created_at": "2026-05-13T00:00:00.000Z",
                    "updated_at": "2026-05-13T00:00:00.000Z",
                },
            )
        )
        await session.commit()

    with patch("generation.routes.run_block_generation", new=AsyncMock(return_value={"headline": "x"})) as mocked:
        async with _client() as client:
            res = await client.post(
                "/api/v1/blocks/generate",
                json={
                    "lesson_id": "lesson-owned-by-other",
                    "component_id": "hook-hero",
                    "mode": "fill",
                    "subject": "Biology",
                    "focus": "Photosynthesis intro",
                    "grade_band": "secondary",
                    "context_blocks": [],
                },
            )

    assert res.status_code == 404
    mocked.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_block_accepts_owned_lesson_and_mode(db_session_factory) -> None:
    app.dependency_overrides[get_current_user] = _override_user
    await _install_session_override(db_session_factory)

    async with db_session_factory() as session:
        session.add(UserModel(id=TEST_USER.id, email=TEST_USER.email, name=TEST_USER.name))
        session.add(
            EditableLessonModel(
                id="lesson-owned-by-user",
                user_id=TEST_USER.id,
                source_type="manual",
                title="My lesson",
                document_json={
                    "version": 1,
                    "id": "lesson-owned-by-user",
                    "title": "My lesson",
                    "subject": "science",
                    "preset_id": "blue-classroom",
                    "source": "manual",
                    "sections": [],
                    "blocks": {},
                    "media": {},
                    "created_at": "2026-05-13T00:00:00.000Z",
                    "updated_at": "2026-05-13T00:00:00.000Z",
                },
            )
        )
        await session.commit()

    with patch("generation.routes.run_block_generation", new=AsyncMock(return_value={"headline": "ok"})) as mocked:
        async with _client() as client:
            res = await client.post(
                "/api/v1/blocks/generate",
                json={
                    "lesson_id": "lesson-owned-by-user",
                    "component_id": "hook-hero",
                    "mode": "custom",
                    "subject": "Biology",
                    "focus": "Photosynthesis intro",
                    "grade_band": "secondary",
                    "teacher_note": "Use simple language.",
                    "context_blocks": [],
                },
            )

    assert res.status_code == 200
    forwarded_body = mocked.await_args.args[0]
    assert forwarded_body.lesson_id == "lesson-owned-by-user"
    assert forwarded_body.mode == "custom"
    assert mocked.await_args.kwargs["user_id"] == TEST_USER.id
