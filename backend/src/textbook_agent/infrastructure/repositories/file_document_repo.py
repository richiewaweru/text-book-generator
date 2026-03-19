from __future__ import annotations

import asyncio
import json
from pathlib import Path

from pipeline.api import PipelineDocument
from textbook_agent.domain.ports.document_repository import DocumentRepository


class FileDocumentRepository(DocumentRepository):
    def __init__(self, output_dir: str) -> None:
        self._root = Path(output_dir)

    def _path_for(self, generation_id: str) -> Path:
        return self._root / f"{generation_id}.json"

    async def save_document(self, document: PipelineDocument) -> str:
        path = self._path_for(document.generation_id)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        payload = document.model_dump(mode="json", exclude_none=True)
        await asyncio.to_thread(
            path.write_text,
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return str(path.resolve())

    async def load_document(self, path: str) -> PipelineDocument:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(path)
        raw = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        return PipelineDocument.model_validate_json(raw)
