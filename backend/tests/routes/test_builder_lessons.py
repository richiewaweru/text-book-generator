from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.dependencies import get_gcs_image_store
from core.database.models import GenerationModel, UserModel
from core.database.session import get_async_session
from core.entities.user import User


def _now() -> datetime:
    return datetime.now(timezone.utc)


USER_A = User(
    id="builder-user-a",
    email="builder-a@example.com",
    name="Builder A",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
)

USER_B = User(
    id="builder-user-b",
    email="builder-b@example.com",
    name="Builder B",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
)


def _minimal_lesson(document_id: str = "client-doc-id") -> dict:
    block_id = "block-1"
    return {
        "version": 1,
        "id": document_id,
        "title": "Fractions basics",
        "subject": "mathematics",
        "preset_id": "blue-classroom",
        "source": "manual",
        "sections": [
            {
                "id": "section-1",
                "template_id": "open-canvas",
                "title": "Fractions basics",
                "position": 0,
                "block_ids": [block_id],
            }
        ],
        "blocks": {
            block_id: {
                "id": block_id,
                "component_id": "explanation-block",
                "position": 0,
                "content": {"body": "A fraction represents part of a whole."},
            }
        },
        "media": {},
        "created_at": "2026-05-13T00:00:00Z",
        "updated_at": "2026-05-13T00:00:00Z",
    }


class _FakeGcsStore:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.calls: list[dict[str, str | int]] = []

    async def upload_with_key(
        self, *, key: str, image_bytes: bytes, content_type: str = "image/png"
    ) -> str | None:
        self.calls.append(
            {
                "key": key,
                "content_type": content_type,
                "size": len(image_bytes),
            }
        )
        return f"https://cdn.example.test/{key}"


@pytest.fixture(autouse=True)
def _install_dependency_overrides(db_session_factory):
    state = {"user": USER_A, "gcs_store": _FakeGcsStore()}

    async def override_current_user():
        return state["user"]

    async def override_session():
        async with db_session_factory() as session:
            yield session

    def override_gcs_store():
        return state["gcs_store"]

    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_async_session] = override_session
    app.dependency_overrides[get_gcs_image_store] = override_gcs_store
    yield state
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def _seed_users_and_generations(db_session_factory):
    async with db_session_factory() as session:
        session.add(
            UserModel(
                id=USER_A.id,
                email=USER_A.email,
                name=USER_A.name,
            )
        )
        session.add(
            UserModel(
                id=USER_B.id,
                email=USER_B.email,
                name=USER_B.name,
            )
        )
        session.add(
            GenerationModel(
                id="gen-owned-by-a",
                user_id=USER_A.id,
                subject="mathematics",
                context="",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                status="completed",
            )
        )
        session.add(
            GenerationModel(
                id="gen-owned-by-b",
                user_id=USER_B.id,
                subject="physics",
                context="",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                status="completed",
            )
        )
        await session.commit()


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestBuilderLessonRoutes:
    async def test_create_load_update_list_and_delete(self):
        create_body = {
            "source_type": "manual",
            "title": "Fractions draft",
            "document": _minimal_lesson(),
        }

        async with await _client() as client:
            create_response = await client.post("/api/v1/builder/lessons", json=create_body)
            assert create_response.status_code == 201
            created = create_response.json()
            lesson_id = created["id"]
            assert created["source_type"] == "manual"
            assert created["title"] == "Fractions draft"
            assert created["document"]["id"] == lesson_id
            assert created["document"]["title"] == "Fractions draft"

            list_response = await client.get("/api/v1/builder/lessons")
            assert list_response.status_code == 200
            listed = list_response.json()
            assert len(listed) == 1
            assert listed[0]["id"] == lesson_id

            load_response = await client.get(f"/api/v1/builder/lessons/{lesson_id}")
            assert load_response.status_code == 200
            loaded = load_response.json()
            block_id = loaded["document"]["sections"][0]["block_ids"][0]
            loaded["document"]["blocks"][block_id]["content"] = {"body": "Updated explanation"}

            update_response = await client.put(
                f"/api/v1/builder/lessons/{lesson_id}",
                json={"title": "Fractions final", "document": loaded["document"]},
            )
            assert update_response.status_code == 200
            updated = update_response.json()
            assert updated["title"] == "Fractions final"
            assert updated["document"]["id"] == lesson_id
            assert updated["document"]["blocks"][block_id]["content"]["body"] == "Updated explanation"

            delete_response = await client.delete(f"/api/v1/builder/lessons/{lesson_id}")
            assert delete_response.status_code == 204
            after_delete = await client.get(f"/api/v1/builder/lessons/{lesson_id}")
            assert after_delete.status_code == 404

    async def test_owner_checks_block_cross_user_access(self, _install_dependency_overrides):
        async with await _client() as client:
            created = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": _minimal_lesson()},
            )
            assert created.status_code == 201
            lesson_id = created.json()["id"]

            _install_dependency_overrides["user"] = USER_B
            forbidden_get = await client.get(f"/api/v1/builder/lessons/{lesson_id}")
            forbidden_put = await client.put(
                f"/api/v1/builder/lessons/{lesson_id}",
                json={"document": _minimal_lesson(document_id=lesson_id)},
            )
            forbidden_delete = await client.delete(f"/api/v1/builder/lessons/{lesson_id}")

        assert forbidden_get.status_code == 404
        assert forbidden_put.status_code == 404
        assert forbidden_delete.status_code == 404

    async def test_create_from_generation_requires_owned_generation(self):
        async with await _client() as client:
            ok_response = await client.post(
                "/api/v1/builder/lessons",
                json={
                    "source_type": "v3_generation",
                    "source_generation_id": "gen-owned-by-a",
                    "document": _minimal_lesson(),
                },
            )
            assert ok_response.status_code == 201

            denied_response = await client.post(
                "/api/v1/builder/lessons",
                json={
                    "source_type": "v3_generation",
                    "source_generation_id": "gen-owned-by-b",
                    "document": _minimal_lesson(),
                },
            )
            assert denied_response.status_code == 404

    async def test_rejects_unknown_component_and_bad_section_references(self):
        invalid_component = _minimal_lesson()
        block_id = invalid_component["sections"][0]["block_ids"][0]
        invalid_component["blocks"][block_id]["component_id"] = "not-a-real-component"

        bad_reference = _minimal_lesson()
        bad_reference["sections"][0]["block_ids"] = ["missing-block"]

        async with await _client() as client:
            unknown_component_response = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": invalid_component},
            )
            missing_block_response = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": bad_reference},
            )

        assert unknown_component_response.status_code == 400
        assert missing_block_response.status_code == 422

    async def test_media_upload_uses_gcs_with_lesson_owned_path(self, _install_dependency_overrides):
        async with await _client() as client:
            created = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": _minimal_lesson()},
            )
            assert created.status_code == 201
            lesson_id = created.json()["id"]

            upload = await client.post(
                f"/api/v1/builder/lessons/{lesson_id}/media/upload",
                files={"file": ("diagram.png", b"\x89PNG\r\n\x1a\nfake-image", "image/png")},
            )

        assert upload.status_code == 200
        body = upload.json()
        assert body["type"] == "image"
        assert body["mime_type"] == "image/png"
        assert body["url"].startswith("https://cdn.example.test/editable-lessons/")
        calls = _install_dependency_overrides["gcs_store"].calls
        assert len(calls) == 1
        assert calls[0]["key"].startswith(f"editable-lessons/{lesson_id}/media/")
        assert calls[0]["content_type"] == "image/png"

    async def test_media_upload_requires_lesson_ownership(self, _install_dependency_overrides):
        async with await _client() as client:
            created = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": _minimal_lesson()},
            )
            assert created.status_code == 201
            lesson_id = created.json()["id"]

            _install_dependency_overrides["user"] = USER_B
            denied = await client.post(
                f"/api/v1/builder/lessons/{lesson_id}/media/upload",
                files={"file": ("diagram.png", b"\x89PNG\r\n\x1a\nfake-image", "image/png")},
            )

        assert denied.status_code == 404

    async def test_media_upload_rejects_unsupported_content_type(self):
        async with await _client() as client:
            created = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": _minimal_lesson()},
            )
            assert created.status_code == 201
            lesson_id = created.json()["id"]

            upload = await client.post(
                f"/api/v1/builder/lessons/{lesson_id}/media/upload",
                files={"file": ("note.txt", b"not-an-image", "text/plain")},
            )

        assert upload.status_code == 415

    async def test_media_upload_rejects_oversized_file(self):
        async with await _client() as client:
            created = await client.post(
                "/api/v1/builder/lessons",
                json={"source_type": "manual", "document": _minimal_lesson()},
            )
            assert created.status_code == 201
            lesson_id = created.json()["id"]

            oversized = b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024 + 1)
            upload = await client.post(
                f"/api/v1/builder/lessons/{lesson_id}/media/upload",
                files={"file": ("huge.png", oversized, "image/png")},
            )

        assert upload.status_code == 413
