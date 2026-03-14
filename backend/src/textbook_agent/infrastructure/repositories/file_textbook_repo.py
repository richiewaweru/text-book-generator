import json
import re
from datetime import datetime
from pathlib import Path

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.textbook_repository import TextbookRepository

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class FileTextbookRepository(TextbookRepository):
    """Persists generated textbooks to the local filesystem."""

    def __init__(self, output_dir: str = "outputs/") -> None:
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, textbook: RawTextbook, html: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = (
            f"{self._slugify(textbook.subject)}-{textbook.profile.age}"
            f"-{textbook.profile.depth.value}-{timestamp}"
        )

        html_name = f"{base_name}.html"
        meta_name = f"{base_name}_meta.json"
        html_path = self.output_dir / html_name
        meta_path = self.output_dir / meta_name

        html_path.write_text(html, encoding="utf-8")
        meta_path.write_text(
            textbook.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return html_name

    async def load_metadata(self, textbook_id: str) -> dict:
        meta_path = self._resolve_path(f"{textbook_id}_meta.json")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    async def load_html(self, output_path: str) -> str:
        file_path = self._resolve_path(output_path)
        if not file_path.exists() or file_path.suffix != ".html":
            raise FileNotFoundError(output_path)
        return file_path.read_text(encoding="utf-8")

    async def load_textbook(self, output_path: str) -> RawTextbook:
        html_path = self._resolve_path(output_path)
        meta_path = html_path.with_name(f"{html_path.stem}_meta.json")
        if not meta_path.exists():
            raise FileNotFoundError(str(meta_path))
        return RawTextbook.model_validate_json(meta_path.read_text(encoding="utf-8"))

    def resolve_output_path(self, output_path: str) -> Path:
        return self._resolve_path(output_path)

    def _resolve_path(self, output_path: str) -> Path:
        candidate = Path(output_path)
        resolved = candidate.resolve() if candidate.is_absolute() else (self.output_dir / candidate).resolve()
        try:
            resolved.relative_to(self.output_dir)
        except ValueError as exc:
            raise ValueError("Output path escapes configured output directory") from exc
        return resolved

    @staticmethod
    def _slugify(value: str) -> str:
        slug = _SLUG_RE.sub("-", value.lower()).strip("-")
        return slug or "textbook"
