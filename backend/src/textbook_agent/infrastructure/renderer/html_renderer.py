from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.renderer import RendererPort

_ASSETS_DIR = Path(__file__).parent / "assets"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


class HTMLRenderer(RendererPort):
    """Renders a RawTextbook into a self-contained HTML file.

    Pure Python - no LLM calls. Uses the design system from base.css.
    All intelligence lives in the pipeline nodes; this is mechanical assembly.
    """

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )
        self._base_css = (_ASSETS_DIR / "base.css").read_text(encoding="utf-8")
        self._prism_css = (_ASSETS_DIR / "prism.css").read_text(encoding="utf-8")

    def render(self, textbook: RawTextbook) -> str:
        section_map = {s.section_id: s for s in textbook.sections}
        diagram_map = {d.section_id: d for d in textbook.diagrams}
        code_map = {c.section_id: c for c in textbook.code_examples}
        spec_map = {s.id: s for s in textbook.plan.sections}

        template = self._env.get_template("textbook.html.j2")
        return template.render(
            textbook=textbook,
            section_map=section_map,
            diagram_map=diagram_map,
            code_map=code_map,
            spec_map=spec_map,
            base_css=self._base_css,
            prism_css=self._prism_css,
        )
