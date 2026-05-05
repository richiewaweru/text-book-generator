from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.database.models import UserModel
from core.database.session import async_session_factory
from core.entities.user import User
from generation.v3_studio.session_store import v3_studio_store
from telemetry.v3_trace import event_types as trace_events
from telemetry.v3_trace.repository import V3TraceRepository

TEST_USER_A = User(
    id="v3-studio-user-a",
    email="v3a@example.com",
    name="V3 Studio A",
    picture_url=None,
    has_profile=True,
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)

TEST_USER_B = User(
    id="v3-studio-user-b",
    email="v3b@example.com",
    name="V3 Studio B",
    picture_url=None,
    has_profile=True,
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)


def _example_bp(name: str):
    from v3_blueprint.models import ProductionBlueprint

    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / name
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


async def _override_user_a() -> User:
    return TEST_USER_A


async def _override_user_b() -> User:
    return TEST_USER_B


async def _ensure_user(user: User) -> None:
    async with async_session_factory() as session:
        model = await session.get(UserModel, user.id)
        if model is None:
            session.add(
                UserModel(
                    id=user.id,
                    email=user.email,
                    name=user.name,
                    picture_url=user.picture_url,
                )
            )
            await session.commit()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset_app_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_v3_generate_start_returns_json_and_sse_stream_closes() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    async def fake_pump(queue, *, blueprint, generation_id, blueprint_id, template_id, **_kwargs):
        _ = blueprint, generation_id, blueprint_id, template_id
        await queue.put("event: component_ready\ndata: {}\n\n")
        await queue.put(None)

    with patch("generation.v3_studio.router._pump_sse_to_queue", new=fake_pump):
        async with _client() as client:
            post = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                    "template_id": "guided-concept-path",
                },
            )
            assert post.status_code == 200
            assert post.json() == {"generation_id": generation_id}

            async with client.stream(
                "GET",
                f"/api/v1/v3/generations/{generation_id}/events",
            ) as resp:
                assert resp.status_code == 200
                payload = await resp.aread()
                assert b"component_ready" in payload

    assert await v3_studio_store.get_queue(generation_id) is None


@pytest.mark.asyncio
async def test_v3_generate_start_conflict_when_generation_id_reused() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    async def fake_pump(queue, **_kwargs):
        await queue.put(None)

    with patch("generation.v3_studio.router._pump_sse_to_queue", new=fake_pump):
        async with _client() as client:
            first = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                },
            )
            assert first.status_code == 200
            second = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                },
            )
            assert second.status_code == 409


@pytest.mark.asyncio
async def test_v3_generation_events_forbidden_for_other_user() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)
    await _ensure_user(TEST_USER_B)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    async def fake_pump(queue, **_kwargs):
        await queue.put(None)

    with patch("generation.v3_studio.router._pump_sse_to_queue", new=fake_pump):
        async with _client() as client:
            await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                },
            )

    app.dependency_overrides[get_current_user] = _override_user_b

    async with _client() as client:
        resp = await client.get(f"/api/v1/v3/generations/{generation_id}/events")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_v3_blueprint_surfaces_exception_details_and_logs() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)
    payload = {
        "signals": {
            "topic": "Area",
            "subtopic": "Compound area",
            "prior_knowledge": ["rectangle area"],
            "learner_needs": [],
            "teacher_goal": "Build confidence",
            "inferred_resource_type": "worksheet",
            "confidence": "medium",
            "missing_signals": [],
        },
        "form": {
            "grade_level": "Grade 8",
            "subject": "Mathematics",
            "duration_minutes": 50,
            "topic": "Compound area (L-shapes)",
            "subtopics": ["L-shapes"],
            "prior_knowledge": "Rectangle area",
            "lesson_mode": "first_exposure",
            "lesson_mode_other": "",
            "intended_outcome": "understand",
            "intended_outcome_other": "",
            "learner_level": "on_grade",
            "reading_level": "on_grade",
            "language_support": "none",
            "prior_knowledge_level": "some_background",
            "support_needs": [],
            "learning_preferences": [],
            "free_text": "Teach compound area with scaffolded examples.",
        },
        "clarification_answers": [],
    }
    with (
        patch(
            "generation.v3_studio.router.generate_production_blueprint",
            side_effect=RuntimeError("architect exploded"),
        ),
        patch("generation.v3_studio.router.logger.exception") as logger_exception,
    ):
        async with _client() as client:
            resp = await client.post("/api/v1/v3/blueprint", json=payload)
    assert resp.status_code == 500
    assert "RuntimeError: architect exploded" in resp.json()["detail"]
    logger_exception.assert_called_once()


@pytest.mark.asyncio
async def test_v3_blueprint_adjust_preserves_learner_context() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)
    bp = _example_bp("amara_compound_area.json")
    payload = {
        "signals": {
            "topic": "Area",
            "subtopic": "Compound area",
            "prior_knowledge": ["rectangle area"],
            "learner_needs": [],
            "teacher_goal": "Build confidence",
            "inferred_resource_type": "worksheet",
            "confidence": "medium",
            "missing_signals": [],
        },
        "form": {
            "grade_level": "Grade 8",
            "subject": "Mathematics",
            "duration_minutes": 50,
            "topic": "Compound area (L-shapes)",
            "subtopics": ["L-shapes"],
            "prior_knowledge": "Rectangle area",
            "lesson_mode": "first_exposure",
            "lesson_mode_other": "",
            "intended_outcome": "understand",
            "intended_outcome_other": "",
            "learner_level": "on_grade",
            "reading_level": "on_grade",
            "language_support": "none",
            "prior_knowledge_level": "some_background",
            "support_needs": ["visuals"],
            "learning_preferences": [],
            "free_text": "Teach compound area with scaffolded examples.",
        },
        "clarification_answers": [],
    }
    with (
        patch("generation.v3_studio.router.generate_production_blueprint", return_value=bp),
        patch("generation.v3_studio.router.adjust_production_blueprint", return_value=bp),
    ):
        async with _client() as client:
            create_resp = await client.post("/api/v1/v3/blueprint", json=payload)
            assert create_resp.status_code == 200
            created = create_resp.json()
            assert created["learner_context"]["grade_level"] == "Grade 8"
            blueprint_id = created["blueprint_id"]

            adjust_resp = await client.post(
                "/api/v1/v3/blueprint/adjust",
                json={
                    "blueprint_id": blueprint_id,
                    "adjustment": "Tighten practice section.",
                },
            )
            assert adjust_resp.status_code == 200
            adjusted = adjust_resp.json()
            assert adjusted["learner_context"]["grade_level"] == "Grade 8"
            assert adjusted["learner_context"]["support_needs"] == ["visuals"]


@pytest.mark.asyncio
async def test_v3_generate_start_creates_trace_before_stream_open() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    async def fake_pump(queue, **_kwargs):
        await queue.put(None)

    with patch("generation.v3_studio.router._pump_sse_to_queue", new=fake_pump):
        async with _client() as client:
            post = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                    "template_id": "guided-concept-path",
                },
            )
            assert post.status_code == 200

    repo = V3TraceRepository(async_session_factory)
    run = await repo.get_run_by_generation(generation_id)
    assert run is not None
    events = await repo.get_events(run.trace_id)
    event_types = [event.event_type for event in events]
    assert trace_events.GENERATION_START_REQUESTED in event_types
    assert trace_events.BLUEPRINT_SNAPSHOT_SAVED in event_types


@pytest.mark.asyncio
async def test_v3_generate_start_fails_when_trace_initialization_fails() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    with patch(
        "generation.v3_studio.router.V3TraceWriter.start_run",
        side_effect=RuntimeError("trace down"),
    ):
        async with _client() as client:
            post = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                    "template_id": "guided-concept-path",
                },
            )
            assert post.status_code == 500
            assert "telemetry could not be initialized" in post.json()["detail"].lower()

    assert await v3_studio_store.get_queue(generation_id) is None


@pytest.mark.asyncio
async def test_v3_trace_endpoints_are_user_scoped() -> None:
    app.dependency_overrides[get_current_user] = _override_user_a
    await _ensure_user(TEST_USER_A)
    await _ensure_user(TEST_USER_B)

    blueprint_id = str(uuid.uuid4())
    generation_id = str(uuid.uuid4())
    bp = _example_bp("amara_compound_area.json")
    await v3_studio_store.put_blueprint(TEST_USER_A.id, blueprint_id, bp, "guided-concept-path")

    async def fake_pump(queue, **_kwargs):
        await queue.put(None)

    with patch("generation.v3_studio.router._pump_sse_to_queue", new=fake_pump):
        async with _client() as client:
            post = await client.post(
                "/api/v1/v3/generate/start",
                json={
                    "generation_id": generation_id,
                    "blueprint_id": blueprint_id,
                    "template_id": "guided-concept-path",
                },
            )
            assert post.status_code == 200

            by_generation = await client.get(f"/api/v1/v3/generations/{generation_id}/trace")
            assert by_generation.status_code == 200
            body = by_generation.json()
            assert body["generation_id"] == generation_id
            assert body["trace_id"]

            by_trace = await client.get(f"/api/v1/v3/traces/{body['trace_id']}")
            assert by_trace.status_code == 200
            assert by_trace.json()["trace_id"] == body["trace_id"]

    app.dependency_overrides[get_current_user] = _override_user_b
    async with _client() as client:
        other_user_resp = await client.get(f"/api/v1/v3/generations/{generation_id}/trace")
        assert other_user_resp.status_code == 404
