import re
from html import escape
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from latex2mathml.converter import convert as latex_to_mathml

from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.ports.renderer import RendererPort

_ASSETS_DIR = Path(__file__).parent / "assets"
_TEMPLATES_DIR = Path(__file__).parent / "templates"
_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_DISPLAY_MATH_RE = re.compile(
    r"^\s*(?:\$\$(?P<dollar>.+?)\$\$|\\\[(?P<bracket>.+?)\\\])\s*$",
    re.DOTALL,
)
_INLINE_MATH_RE = re.compile(
    r"(\\\((?P<paren>.+?)\\\)|(?<!\$)\$(?!\$)(?P<dollar>.+?)(?<!\$)\$(?!\$))",
    re.DOTALL,
)


def _escape_html(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _render_math(expression: str, *, display: str) -> str:
    cleaned = expression.strip()
    if not cleaned:
        return ""
    try:
        return latex_to_mathml(cleaned, display=display)
    except Exception:
        if display == "block":
            return f"<pre class=\"math-fallback\">{_escape_html(cleaned)}</pre>"
        return f"<code class=\"math-fallback\">{_escape_html(cleaned)}</code>"


def _render_inline_markup(line: str) -> str:
    rendered: list[str] = []
    cursor = 0
    for match in _INLINE_MATH_RE.finditer(line):
        start, end = match.span()
        rendered.append(_escape_html(line[cursor:start]))
        expression = match.group("paren") or match.group("dollar") or ""
        rendered.append(_render_math(expression, display="inline"))
        cursor = end
    rendered.append(_escape_html(line[cursor:]))
    return "".join(rendered)


def _render_text_block(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""

    blocks = []
    for paragraph in _PARAGRAPH_RE.split(text):
        normalized = paragraph.strip()
        if not normalized:
            continue

        display_match = _DISPLAY_MATH_RE.fullmatch(normalized)
        if display_match:
            expression = display_match.group("dollar") or display_match.group("bracket") or ""
            blocks.append(f"<div class=\"math-block\">{_render_math(expression, display='block')}</div>")
            continue

        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            continue
        blocks.append(f"<p>{'<br>'.join(_render_inline_markup(line) for line in lines)}</p>")
    return "".join(blocks)


class HTMLRenderer(RendererPort):
    """Renders a RawTextbook into a standalone HTML document."""

    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._env.globals["escape_html"] = _escape_html
        self._env.globals["render_text_block"] = _render_text_block
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
