from __future__ import annotations

from datetime import datetime
import json
from types import SimpleNamespace

import pytest

from app import app
from core.database.models import GenerationModel, UserModel
from generation.canonical import (
    CANONICAL_PIPELINE,
    build_pipeline_document_for_lesson_document,
    canonical_document,
    get_owned_canonical_generation,
    list_owned_canonical_generations,
    pipeline_marker,
)
from generation import canonical_routes
from generation.pdf_export.service import PDFExportResult
from learning.routes import get_pack_document


def _document(generation_id: str) -> dict:
    return {
        "version": 1,
        "id": generation_id,
        "title": "Canonical lesson",
        "subject": "Mathematics",
        "preset_id": "blue-classroom",
        "source": "generated",
        "source_generation_id": generation_id,
        "sections": [
            {
                "id": "intro",
                "template_id": "guided-concept-path",
                "block_ids": ["intro-heading"],
                "title": "Introduction",
                "position": 1,
            }
        ],
        "blocks": {
            "intro-heading": {
                "id": "intro-heading",
                "component_id": "section-header",
                "content": {"title": "Introduction"},
                "position": 1,
            }
        },
        "media": {},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _generation(generation_id: str, *, pipeline: str | None) -> GenerationModel:
    state = {"stage": "complete"}
    if pipeline:
        state["control"] = {"pipeline": pipeline}
    return GenerationModel(
        id=generation_id,
        user_id="canonical-user",
        subject="Mathematics",
        context="Fractions",
        mode="balanced",
        status="completed",
        document_json=_document(generation_id),
        chunked_state_json=state,
        requested_template_id="guided-concept-path",
        requested_preset_id="blue-classroom",
        created_at=datetime(2026, 1, 1),
    )


def test_pipeline_marker_never_infers_missing_rows() -> None:
    canonical = _generation("canonical", pipeline=CANONICAL_PIPELINE)
    legacy = _generation("legacy", pipeline="v3_studio")
    unmarked = _generation("unmarked", pipeline=None)

    assert pipeline_marker(canonical) == CANONICAL_PIPELINE
    assert pipeline_marker(legacy) == "v3_studio"
    assert pipeline_marker(unmarked) is None
    assert canonical_document(canonical) is not None
    assert canonical_document(legacy) is None
    assert canonical_document(unmarked) is None


@pytest.mark.asyncio
async def test_generation_queries_only_return_explicit_component_rows(db_session) -> None:
    db_session.add(UserModel(id="canonical-user", email="canonical@example.invalid"))
    db_session.add(_generation("canonical", pipeline=CANONICAL_PIPELINE))
    db_session.add(_generation("legacy", pipeline="v3_studio"))
    db_session.add(_generation("unmarked", pipeline=None))
    await db_session.commit()

    rows = await list_owned_canonical_generations(db_session, user_id="canonical-user")
    assert [row.id for row in rows] == ["canonical"]
    assert await get_owned_canonical_generation(
        db_session, generation_id="legacy", user_id="canonical-user"
    ) is None


def test_canonical_document_projects_pdf_metadata_without_runtime_fields() -> None:
    generation = _generation("canonical", pipeline=CANONICAL_PIPELINE)
    projected = build_pipeline_document_for_lesson_document(generation=generation)

    assert projected.generation_id == "canonical"
    assert projected.mode == "component_lectio"
    assert projected.subject == "Canonical lesson"
    assert projected.section_manifest[0].section_id == "intro"
    assert projected.status == "completed"


def test_canonical_generation_router_is_mounted_outside_retired_v3_namespace() -> None:
    paths = app.openapi()["paths"]

    assert "/api/v1/generations" in paths
    assert "/api/v1/generations/{generation_id}/document" in paths
    assert "/api/v1/generations/{generation_id}/export/pdf" in paths
    assert "/api/v1/v3/generations" not in paths


@pytest.mark.asyncio
async def test_canonical_pdf_uses_builder_lesson_id_for_print_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    generation = _generation("generation-id", pipeline=CANONICAL_PIPELINE)
    captured: dict[str, str] = {}

    async def fake_lookup(*args, **kwargs):
        return generation

    async def fake_builder_id(*args, **kwargs):
        return "builder-lesson-id"

    async def fake_export(**kwargs):
        captured["render_path"] = kwargs["render_path"]
        output = tmp_path / "lesson.pdf"
        output.write_bytes(b"%PDF-1.4\n")
        return PDFExportResult(
            pdf_path=output,
            filename="lesson.pdf",
            file_size_bytes=output.stat().st_size,
            page_count=1,
            generation_time_ms=1,
            cleanup_paths=[],
        )

    monkeypatch.setattr(canonical_routes, "_canonical_or_404", fake_lookup)
    monkeypatch.setattr(canonical_routes, "builder_id_for_generation", fake_builder_id)
    monkeypatch.setattr(canonical_routes, "export_canonical_generation_pdf", fake_export)
    monkeypatch.setattr(canonical_routes, "get_settings", lambda: SimpleNamespace())

    class _JWT:
        def create_access_token(self, user_id: str, email: str) -> str:
            return f"token:{user_id}:{email}"

    response = await canonical_routes.export_generation_pdf_route(
        "generation-id",
        canonical_routes.CanonicalGenerationPDFExportRequest(
            school_name="School", teacher_name="Teacher"
        ),
        SimpleNamespace(state=SimpleNamespace(request_id=None)),
        SimpleNamespace(id="canonical-user", email="canonical@example.invalid"),
        None,
        _JWT(),
    )

    assert response.media_type == "application/pdf"
    assert captured["render_path"] == "/builder/print/builder-lesson-id"
    assert "generation-id" not in captured["render_path"]


@pytest.mark.asyncio
async def test_canonical_pack_document_keeps_planned_pending_resources() -> None:
    generation = _generation("generation-r1", pipeline=CANONICAL_PIPELINE)
    generation.pack_resource_id = "r1"
    unknown_generation = _generation("generation-unknown", pipeline=CANONICAL_PIPELINE)
    unknown_generation.pack_resource_id = "r-unknown"
    pack = SimpleNamespace(
        id="pack-1",
        user_id="canonical-user",
        subject="Mathematics",
        topic="Fractions",
        pack_plan_json=json.dumps(
            {
                "resources": [
                    {"id": "r1", "label": "Core lesson"},
                    {"id": "r2", "label": "Practice lesson"},
                ]
            }
        ),
    )

    class _PackRepository:
        async def find_by_id(self, pack_id: str):
            return pack if pack_id == pack.id else None

        async def component_generations_for_pack(self, pack_id: str):
            return [generation, unknown_generation] if pack_id == pack.id else []

    response = await get_pack_document(
        "pack-1",
        SimpleNamespace(id="canonical-user"),
        _PackRepository(),
    )

    assert [resource.resource_id for resource in response.resources] == [
        "r1",
        "r2",
        "generation-unknown",
    ]
    assert response.resources[0].document is not None
    assert response.resources[1].generation_id is None
    assert response.resources[1].document is None
    assert response.resources[1].status == "pending"
    assert response.resources[2].generation_id == "generation-unknown"
    assert response.resources[2].document is not None
