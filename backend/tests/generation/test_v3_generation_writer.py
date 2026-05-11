from __future__ import annotations

from sqlalchemy import delete, select

from core.database.models import GenerationModel
from core.database.session import async_session_factory
from generation.v3_studio.generation_writer import V3GenerationWriter


async def _cleanup_generation(generation_id: str) -> None:
    async with async_session_factory() as session:
        await session.execute(delete(GenerationModel).where(GenerationModel.id == generation_id))
        await session.commit()


async def _load_generation(generation_id: str) -> GenerationModel:
    async with async_session_factory() as session:
        result = await session.execute(
            select(GenerationModel).where(GenerationModel.id == generation_id)
        )
        model = result.scalar_one_or_none()
        assert model is not None
        return model


async def test_v3_generation_writer_persists_flat_document_json_and_report_snapshot() -> None:
    generation_id = "v3-writer-draft"
    await _cleanup_generation(generation_id)
    writer = V3GenerationWriter(async_session_factory)
    try:
        await writer.upsert_started(
            generation_id=generation_id,
            user_id="writer-user",
            subject="Science",
            context="Plants",
            template_id="guided-concept-path",
            section_count=3,
            planned_visuals=2,
            planned_questions=4,
            component_count=9,
        )
        await writer.write_draft(
            generation_id,
            {
                "booklet_status": "draft_ready",
                "pack": {
                    "generation_id": generation_id,
                    "blueprint_id": "bp-1",
                    "template_id": "guided-concept-path",
                    "subject": "Science",
                    "status": "draft_ready",
                    "sections": [{"section_id": "orient", "header": {"title": "Intro"}}],
                    "warnings": [],
                    "section_diagnostics": [],
                    "booklet_issues": [],
                },
            },
        )
        model = await _load_generation(generation_id)
        assert model.status == "running"
        # V3 writer does not set mode=v3; DB server_default is balanced
        assert model.mode == "balanced"
        assert isinstance(model.document_json, dict)
        assert model.document_json["kind"] == "v3_booklet_pack"
        assert model.document_json["status"] == "draft_ready"
        assert isinstance(model.report_json, dict)
        assert model.report_json["pipeline_version"] == "v3"
        assert model.report_json["report_schema"] == "v3_generation_report_v1"
        assert model.report_json["booklet_status"] == "draft_ready"
        assert model.report_json["summary"]["planned_sections"] == 3
        assert model.report_json["summary"]["ready_sections"] == 1
        assert model.report_json["summary"]["missing_sections"] == 2
        assert model.report_json["summary"]["planned_visuals"] == 2
        assert model.report_json["summary"]["planned_questions"] == 4
        assert model.report_json["summary"]["assembled_sections"] == 1
    finally:
        await _cleanup_generation(generation_id)


async def test_v3_generation_writer_handles_resource_finalised_and_pdf_status() -> None:
    generation_id = "v3-writer-final"
    await _cleanup_generation(generation_id)
    writer = V3GenerationWriter(async_session_factory)
    try:
        await writer.upsert_started(
            generation_id=generation_id,
            user_id="writer-user",
            subject="Math",
            context="Triangles",
            template_id="guided-concept-path",
            section_count=2,
            planned_visuals=1,
            planned_questions=2,
            component_count=4,
        )
        await writer.write_draft(
            generation_id,
            {
                "booklet_status": "draft_needs_review",
                "pack": {
                    "generation_id": generation_id,
                    "blueprint_id": "bp-2",
                    "template_id": "guided-concept-path",
                    "subject": "Math",
                    "status": "draft_needs_review",
                    "sections": [
                        {
                            "section_id": "s1",
                            "diagram": {"image_url": "https://cdn.example/one.png"},
                            "practice": {"items": [{"prompt": "1"}]},
                        }
                    ],
                    "warnings": [],
                    "section_diagnostics": [],
                    "booklet_issues": [],
                },
            },
        )
        await writer.write_resource_finalised(
            generation_id,
            {
                "status": "repair_required",
                "booklet_status": "draft_needs_review",
            },
        )
        await writer.write_pdf_status(
            generation_id,
            status="failed",
            error="Playwright timeout",
            debug={"page_url": "https://example/print"},
        )
        model = await _load_generation(generation_id)
        assert model.status == "partial"
        assert model.quality_passed is False
        assert model.completed_at is not None
        assert isinstance(model.report_json, dict)
        assert model.report_json["process_status"] == "failed_finalisation"
        assert model.report_json["summary"]["assembled_sections"] == 1
        assert model.report_json["summary"]["ready_sections"] == 1
        assert model.report_json["summary"]["missing_sections"] == 1
        assert model.report_json["summary"]["delivered_visuals"] == 1
        assert model.report_json["summary"]["delivered_questions"] == 1
        assert model.report_json["pdf"]["last_export_status"] == "failed"
        assert model.report_json["pdf"]["last_error"] == "Playwright timeout"
        assert model.report_json["pdf"]["last_debug"] == {"page_url": "https://example/print"}
    finally:
        await _cleanup_generation(generation_id)


async def test_v3_generation_writer_persists_full_coherence_report() -> None:
    generation_id = "v3-writer-coherence"
    await _cleanup_generation(generation_id)
    writer = V3GenerationWriter(async_session_factory)
    try:
        await writer.upsert_started(
            generation_id=generation_id,
            user_id="writer-user",
            subject="Science",
            context="Cells",
            template_id="guided-concept-path",
            section_count=1,
        )
        coherence = {
            "status": "repair_required",
            "blocking_count": 3,
            "major_count": 1,
            "minor_count": 0,
            "issues": [{"issue_id": "i-1", "severity": "blocking"}],
            "repair_targets": [{"target_id": "t-1"}],
            "repaired_target_ids": [],
        }
        await writer.write_coherence_result(generation_id, coherence)
        await writer.write_generation_complete(
            generation_id,
            {
                "coherence_review": {
                    "status": "repair_required",
                    "blocking_count": 3,
                    "major_count": 1,
                    "minor_count": 0,
                }
            },
        )
        model = await _load_generation(generation_id)
        assert isinstance(model.report_json, dict)
        assert model.report_json["coherence"]["issues"][0]["issue_id"] == "i-1"
        assert model.report_json["summary"]["blocking_issues"] == 3
        assert model.report_json["summary"]["major_issues"] == 1
        assert model.report_json["summary"]["minor_issues"] == 0
        assert model.report_json["summary"]["repair_target_count"] == 1
        assert model.report_json["summary"]["repaired_target_count"] == 0
    finally:
        await _cleanup_generation(generation_id)
