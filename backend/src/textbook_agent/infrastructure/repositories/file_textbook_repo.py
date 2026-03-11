import json
from datetime import datetime
from pathlib import Path

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.textbook_repository import TextbookRepository


class FileTextbookRepository(TextbookRepository):
    """Persists generated textbooks to the local filesystem."""

    def __init__(self, output_dir: str = "outputs/") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, textbook: RawTextbook, html: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = (
            f"{textbook.subject}_{textbook.profile.age}"
            f"_{textbook.profile.depth.value}_{timestamp}"
        )

        html_path = self.output_dir / f"{base_name}.html"
        meta_path = self.output_dir / f"{base_name}_meta.json"

        html_path.write_text(html, encoding="utf-8")
        meta_path.write_text(
            textbook.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return str(html_path)

    async def load_metadata(self, textbook_id: str) -> dict:
        meta_path = self.output_dir / f"{textbook_id}_meta.json"
        return json.loads(meta_path.read_text(encoding="utf-8"))
