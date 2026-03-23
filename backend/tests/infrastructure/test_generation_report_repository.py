from __future__ import annotations

import json

import pytest

from textbook_agent.application.dtos import GenerationReport
from textbook_agent.infrastructure.repositories.file_generation_report_repo import (
    FileGenerationReportRepository,
)


def _report(generation_id: str = "gen-report") -> GenerationReport:
    return GenerationReport(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        mode="balanced",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="running",
        outcome="partial",
        section_count=2,
    )


@pytest.mark.asyncio
async def test_save_and_load_report_round_trip(tmp_path) -> None:
    repo = FileGenerationReportRepository(output_dir=str(tmp_path))
    report = _report()

    path = await repo.save_report(report)

    assert path.endswith("gen-report.json")
    loaded = await repo.load_report("gen-report")
    assert loaded.generation_id == report.generation_id
    assert loaded.template_id == "guided-concept-path"
    assert loaded.outcome == "partial"


@pytest.mark.asyncio
async def test_save_report_replaces_target_atomically_and_cleans_tmp(tmp_path) -> None:
    repo = FileGenerationReportRepository(output_dir=str(tmp_path))

    await repo.save_report(_report("gen-atomic"))
    await repo.save_report(
        _report("gen-atomic").model_copy(
            update={"status": "completed", "generation_time_seconds": 14.2}
        )
    )

    payload = json.loads((tmp_path / "gen-atomic.json").read_text(encoding="utf-8"))
    assert payload["status"] == "completed"
    assert payload["generation_time_seconds"] == 14.2
    assert list(tmp_path.glob("*.tmp")) == []
