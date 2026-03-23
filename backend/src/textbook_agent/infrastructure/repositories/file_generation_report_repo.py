from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pipeline.reporting import GenerationReport
from textbook_agent.domain.ports.generation_report_repository import (
    GenerationReportRepository,
)


class FileGenerationReportRepository(GenerationReportRepository):
    def __init__(self, output_dir: str) -> None:
        self._root = Path(output_dir)

    def _path_for(self, generation_id: str) -> Path:
        return self._root / f"{generation_id}.json"

    async def save_report(self, report: GenerationReport) -> str:
        path = self._path_for(report.generation_id)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        payload = report.model_dump(mode="json", exclude_none=True)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(
            tmp_path.write_text,
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        await asyncio.to_thread(tmp_path.replace, path)
        return str(path.resolve())

    async def load_report(self, generation_id: str) -> GenerationReport:
        path = self._path_for(generation_id)
        if not path.exists():
            raise FileNotFoundError(str(path))
        raw = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return GenerationReport.model_validate_json(raw)

    async def cleanup_tmp(self, generation_id: str) -> None:
        path = self._path_for(generation_id)
        tmp_path = path.with_suffix(f"{path.suffix}.tmp")
        try:
            if await asyncio.to_thread(tmp_path.exists):
                await asyncio.to_thread(tmp_path.unlink)
        except OSError:
            pass
