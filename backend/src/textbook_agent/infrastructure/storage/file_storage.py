import json
from pathlib import Path

from textbook_agent.domain.entities.learner_profile import LearnerProfile
from textbook_agent.domain.ports.file_storage import FileStoragePort


class FileSystemStorage(FileStoragePort):
    """Concrete file storage implementation using the local filesystem."""

    def read_profile(self, path: str) -> LearnerProfile:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return LearnerProfile.model_validate(data)

    def write_output(self, path: str, content: str) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
