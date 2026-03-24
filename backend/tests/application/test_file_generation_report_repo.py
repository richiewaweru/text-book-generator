from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.reporting import GenerationReport, GenerationReportSummary
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
        section_count=1,
        summary=GenerationReportSummary(),
    )


@pytest.mark.asyncio
async def test_cleanup_tmp_removes_leftover_temp_file(tmp_path: Path) -> None:
    repo = FileGenerationReportRepository(str(tmp_path))
    tmp_file = tmp_path / "gen-temp.json.tmp"
    tmp_file.write_text("{}", encoding="utf-8")

    await repo.cleanup_tmp("gen-temp")

    assert tmp_file.exists() is False


@pytest.mark.asyncio
async def test_save_report_retries_atomic_replace_and_cleans_stale_tmp(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo = FileGenerationReportRepository(str(tmp_path))
    stale_tmp = tmp_path / "gen-retry.json.tmp"
    stale_tmp.write_text("stale", encoding="utf-8")

    attempts = 0
    original_replace = Path.replace

    def flaky_replace(self: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if self.name == "gen-retry.json.tmp" and attempts < 3:
            raise PermissionError("busy")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    saved_path = await repo.save_report(_report("gen-retry"))
    loaded = await repo.load_report("gen-retry")

    assert attempts == 3
    assert saved_path.endswith("gen-retry.json")
    assert loaded.generation_id == "gen-retry"
    assert stale_tmp.exists() is False
