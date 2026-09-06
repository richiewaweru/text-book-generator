from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from generation import units_routes
from core.database.models import GenerationModel, LessonProvenanceModel
from planning.models import PathVersionMutationRequest


def _body() -> PathVersionMutationRequest:
    return PathVersionMutationRequest(path_version_id="path-1", path_revision=2)


def _context(state: dict) -> tuple[object, object, object, object, dict]:
    return (
        SimpleNamespace(id="unit-1"),
        SimpleNamespace(id="path-1", revision=2),
        SimpleNamespace(id="lesson-1", pack_id="gen-1"),
        SimpleNamespace(id="gen-1", status="awaiting_review", document_json=None),
        state,
    )


@pytest.mark.asyncio
async def test_status_contains_pipeline_stage_document_and_retry_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        return _context(
            {
                "control": {"pipeline": "component_lectio"},
                "stage": "assembly_blocked",
                "display_title": "Cells",
                "failed_blocks": ["orient.1"],
                "structural_plan": {
                    "cards": [
                        {
                            "id": "cells",
                            "title": "Cell structure",
                            "objective": "Name parts",
                            "prereqs": ["matter"],
                            "misconceptions": [
                                {"description": "A cell is flat."},
                                {"internal": "ignored"},
                            ],
                        }
                    ]
                },
            }
        )

    monkeypatch.setattr(units_routes, "_generation_context", context)
    result = await units_routes.get_units_generation_status(
        "unit-1", "lesson-1", SimpleNamespace(id="user-1"), None
    )
    assert result.pipeline == "component_lectio"
    assert result.stage == "assembly_blocked"
    assert result.failed_blocks == ["orient.1"]
    assert result.retryable is True
    assert result.document_present is False
    assert result.builder_id is None
    assert result.display_title == "Cells"
    assert result.review_cards[0].id == "cells"
    assert result.review_cards[0].misconception_descriptions == ["A cell is flat."]


@pytest.mark.asyncio
async def test_status_prefers_completed_document_over_stale_review_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        result = _context(
            {"control": {"pipeline": "component_lectio"}, "stage": "awaiting_review"}
        )
        result[3].status = "completed"
        result[3].document_json = {"version": 1, "blocks": []}
        return result

    monkeypatch.setattr(units_routes, "_generation_context", context)
    result = await units_routes.get_units_generation_status(
        "unit-1", "lesson-1", SimpleNamespace(id="user-1"), None
    )

    assert result.stage == "complete"
    assert result.document_present is True


@pytest.mark.asyncio
async def test_approve_dispatches_persisted_component_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        return _context({"control": {"pipeline": "component_lectio"}, "stage": "awaiting_review"})

    called: list[str] = []

    async def dispatch(**kwargs):
        called.append(kwargs["generation_id"])
        return "component_lectio"

    monkeypatch.setattr(units_routes, "_generation_context", context)
    monkeypatch.setattr(units_routes, "dispatch_units_generation", dispatch)
    result = await units_routes.approve_units_generation(
        "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), None
    )
    assert called == ["gen-1"]
    assert result.stage == "component_lectio_running"


@pytest.mark.asyncio
async def test_route_rejects_stale_revision_and_missing_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        return _context({"control": {"pipeline": "v3_studio"}, "stage": "awaiting_review"})

    monkeypatch.setattr(units_routes, "_generation_context", context)
    with pytest.raises(HTTPException) as stale:
        await units_routes.approve_units_generation(
            "unit-1",
            "lesson-1",
            PathVersionMutationRequest(path_version_id="path-1", path_revision=1),
            SimpleNamespace(id="user-1"),
            None,
        )
    assert stale.value.status_code == 409
    with pytest.raises(HTTPException) as legacy:
        await units_routes.approve_units_generation(
            "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), None
        )
    assert legacy.value.status_code == 409


@pytest.mark.asyncio
async def test_route_surfaces_ownership_404(monkeypatch: pytest.MonkeyPatch) -> None:
    async def context(*args, **kwargs):
        raise HTTPException(status_code=404, detail="Unit generation not found")

    monkeypatch.setattr(units_routes, "_generation_context", context)
    with pytest.raises(HTTPException) as missing:
        await units_routes.get_units_generation_status(
            "other-unit", "lesson-1", SimpleNamespace(id="user-1"), None
        )
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_retry_rejects_running_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    async def context(*args, **kwargs):
        result = _context(
            {"control": {"pipeline": "component_lectio"}, "stage": "component_lectio_running"}
        )
        result[3].status = "running"
        return result

    monkeypatch.setattr(units_routes, "_generation_context", context)
    with pytest.raises(HTTPException) as blocked:
        await units_routes.retry_units_generation(
            "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), None
        )
    assert blocked.value.status_code == 409


@pytest.mark.asyncio
async def test_approve_completed_generation_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    async def context(*args, **kwargs):
        result = _context({"control": {"pipeline": "component_lectio"}, "stage": "complete"})
        result[3].status = "completed"
        result[3].document_json = {"lesson": True}
        return result

    async def must_not_dispatch(**kwargs):
        raise AssertionError("completed generation must not restart")

    monkeypatch.setattr(units_routes, "_generation_context", context)
    monkeypatch.setattr(units_routes, "dispatch_units_generation", must_not_dispatch)
    result = await units_routes.approve_units_generation(
        "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), None
    )
    assert result.stage == "complete"
    assert result.document_present is True


@pytest.mark.asyncio
async def test_approve_running_generation_returns_status_without_restart(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        result = _context(
            {"control": {"pipeline": "component_lectio"}, "stage": "component_lectio_running"}
        )
        result[3].status = "running"
        return result

    async def must_not_dispatch(**kwargs):
        raise AssertionError("active generation must not restart")

    monkeypatch.setattr(units_routes, "_generation_context", context)
    monkeypatch.setattr(units_routes, "dispatch_units_generation", must_not_dispatch)
    monkeypatch.setattr(
        units_routes,
        "units_dispatch_task",
        lambda generation_id: SimpleNamespace(done=lambda: False),
    )
    result = await units_routes.approve_units_generation(
        "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), None
    )
    assert result.stage == "component_lectio_running"


class _Session:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def scalar(self, statement):
        return "builder-1"


@pytest.mark.asyncio
async def test_generation_context_resolves_current_pack_after_regeneration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unit = SimpleNamespace(id="unit-1", owner_id="user-1")
    lesson = SimpleNamespace(id="lesson-1", path_version_id="path-1", pack_id="gen-current")
    version = SimpleNamespace(id="path-1", unit_id="unit-1", revision=2)
    old = SimpleNamespace(
        pack_id="gen-old", path_version_id="path-1", path_lesson_id="lesson-1", invalidated_at="old"
    )
    current = SimpleNamespace(
        pack_id="gen-current",
        path_version_id="path-1",
        path_lesson_id="lesson-1",
        invalidated_at=None,
    )
    generation = SimpleNamespace(id="gen-current", user_id="user-1")

    class Session:
        async def scalar(self, statement):
            text = str(statement)
            return unit if "units" in text else lesson

        async def get(self, model, key):
            if model is LessonProvenanceModel:
                return current if key == "gen-current" else old
            if model is GenerationModel:
                return generation if key == "gen-current" else None
            return version

    async def state(*args, **kwargs):
        return {}

    monkeypatch.setattr(units_routes, "load_chunked_state", state)
    _unit, _version, _lesson, resolved, _state = await units_routes._generation_context(
        Session(), unit_id="unit-1", lesson_id="lesson-1", user_id="user-1"
    )
    assert resolved.id == "gen-current"


@pytest.mark.asyncio
async def test_open_builder_is_idempotent_and_returns_builder_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        result = _context({"control": {"pipeline": "component_lectio"}, "stage": "complete"})
        result[3].status = "completed"
        result[3].document_json = {"valid": True}
        return result

    calls: list[str] = []

    async def open_builder(session, *, generation, user_id):
        calls.append(generation.id)
        return SimpleNamespace(id="builder-1")

    monkeypatch.setattr(units_routes, "_generation_context", context)
    monkeypatch.setattr(units_routes, "get_or_create_component_lectio_builder_lesson", open_builder)
    result = await units_routes.open_units_builder(
        "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), _Session()
    )
    assert calls == ["gen-1"]
    assert result.builder_id == "builder-1"


@pytest.mark.asyncio
async def test_open_builder_maps_not_ready_and_stale_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def context(*args, **kwargs):
        return _context({"control": {"pipeline": "component_lectio"}, "stage": "awaiting_review"})

    async def not_ready(*args, **kwargs):
        raise units_routes.ComponentLectioBuilderNotReadyError("not ready")

    monkeypatch.setattr(units_routes, "_generation_context", context)
    monkeypatch.setattr(units_routes, "get_or_create_component_lectio_builder_lesson", not_ready)
    with pytest.raises(HTTPException) as blocked:
        await units_routes.open_units_builder(
            "unit-1", "lesson-1", _body(), SimpleNamespace(id="user-1"), _Session()
        )
    assert blocked.value.status_code == 409
    with pytest.raises(HTTPException) as stale:
        await units_routes.open_units_builder(
            "unit-1",
            "lesson-1",
            PathVersionMutationRequest(path_version_id="path-1", path_revision=99),
            SimpleNamespace(id="user-1"),
            _Session(),
        )
    assert stale.value.status_code == 409
