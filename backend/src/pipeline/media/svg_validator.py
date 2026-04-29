from __future__ import annotations

from xml.etree import ElementTree as ET

from pipeline.media.svg_sanitizer import BANNED_TAGS


MAX_SVG_LENGTH = 50_000
VISIBLE_TAGS = {
    "path",
    "line",
    "polyline",
    "polygon",
    "rect",
    "circle",
    "ellipse",
    "text",
    "tspan",
}
GRAPH_BRIEF_TERMS = {
    "slope",
    "gradient",
    "rise",
    "run",
    "coordinate",
    "graph",
    "grid",
}


class SvgValidationError(ValueError):
    """Raised when SVG is safe XML but unsuitable for the requested brief."""


class SvgIntentValidationError(SvgValidationError):
    """Raised when SVG does not match the pedagogical visual intent."""


def _local_name(name: str) -> str:
    if "}" in name:
        return name.rsplit("}", 1)[1]
    return name


def _parse_svg(svg_content: str) -> ET.Element:
    try:
        return ET.fromstring(svg_content.strip())
    except ET.ParseError as exc:
        raise SvgValidationError(f"SVG is not valid XML: {exc}") from exc


def _tag_counts(root: ET.Element) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element in root.iter():
        tag = _local_name(element.tag)
        counts[tag] = counts.get(tag, 0) + 1
    return counts


def validate_svg_basic(svg_content: str) -> None:
    if not svg_content.strip():
        raise SvgValidationError("SVG content is empty")
    if len(svg_content) > MAX_SVG_LENGTH:
        raise SvgValidationError("SVG content is too large")

    root = _parse_svg(svg_content)
    if _local_name(root.tag) != "svg":
        raise SvgValidationError("SVG root must be <svg>")
    if not root.attrib.get("viewBox"):
        raise SvgValidationError("SVG must include a viewBox")

    counts = _tag_counts(root)
    banned = sorted(tag for tag in counts if tag.lower() in BANNED_TAGS)
    if banned:
        raise SvgValidationError(f"SVG contains banned tag(s): {', '.join(banned)}")
    if not any(counts.get(tag, 0) for tag in VISIBLE_TAGS):
        raise SvgValidationError("SVG has no visible diagram elements")


def _is_graph_brief(brief: str) -> bool:
    lowered = brief.lower()
    return any(term in lowered for term in GRAPH_BRIEF_TERMS) or "rise/run" in lowered


def validate_svg_intent(svg_content: str, brief: str | None) -> None:
    if not brief or not _is_graph_brief(brief):
        return

    root = _parse_svg(svg_content)
    counts = _tag_counts(root)
    graph_marks = counts.get("line", 0) + counts.get("path", 0) + counts.get("polyline", 0)
    text_labels = counts.get("text", 0) + counts.get("tspan", 0)
    rects = counts.get("rect", 0)

    if graph_marks == 0:
        raise SvgIntentValidationError(
            "The brief asks for a graph-like diagram, but the SVG has no line/path/polyline marks."
        )
    if text_labels == 0:
        raise SvgIntentValidationError(
            "The brief asks for a graph-like diagram, but the SVG has no text labels."
        )
    if rects >= 2 and rects >= graph_marks:
        raise SvgIntentValidationError(
            "The brief asks for slope/rise-run graphing, but the SVG appears to be a flowchart."
        )
