import json
from pathlib import Path

from textbook_agent.domain.entities.generation_context import GenerationContext
from textbook_agent.domain.ports.file_storage import FileStoragePort


class FileSystemStorage(FileStoragePort):
    """Concrete file storage implementation using the local filesystem."""

    def read_profile(self, path: str) -> GenerationContext:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return GenerationContext.model_validate(data)

    def write_output(self, path: str, content: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
