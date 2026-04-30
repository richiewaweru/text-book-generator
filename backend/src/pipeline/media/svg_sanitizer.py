from __future__ import annotations

import re
from xml.etree import ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

ALLOWED_TAGS = {
    "svg",
    "g",
    "defs",
    "marker",
    "path",
    "line",
    "polyline",
    "polygon",
    "rect",
    "circle",
    "ellipse",
    "text",
    "tspan",
    "title",
    "desc",
}
BANNED_TAGS = {
    "script",
    "foreignobject",
    "iframe",
    "object",
    "embed",
    "canvas",
    "video",
    "audio",
    "image",
}
URL_ATTRS = {"href", "xlink:href"}
_SVG_OPEN_TAG_RE = re.compile(r"(<svg\b)([^>]*)(>)", re.IGNORECASE | re.DOTALL)
_ATTR_RE = re.compile(r"(\s+[\w:.-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'))", re.DOTALL)


class SvgSanitizationError(ValueError):
    """Raised when model-generated SVG cannot be made safe."""


def _local_name(name: str) -> str:
    if "}" in name:
        return name.rsplit("}", 1)[1]
    return name


def _normalized_attr_name(name: str) -> str:
    if name == f"{{{XLINK_NS}}}href":
        return "xlink:href"
    return _local_name(name)


def _reject_unsafe_url(value: str, *, attr_name: str) -> None:
    normalized = value.strip().lower()
    if normalized.startswith(("javascript:", "http:", "https:", "//", "data:")):
        raise SvgSanitizationError(f"unsafe SVG URL in {attr_name}")
    if normalized and not normalized.startswith("#"):
        raise SvgSanitizationError(f"external SVG reference in {attr_name}")


def _dedupe_svg_opening_tag(raw: str) -> str:
    match = _SVG_OPEN_TAG_RE.search(raw)
    if match is None:
        return raw

    prefix, attrs_str, close = match.group(1), match.group(2), match.group(3)
    seen: set[str] = set()
    deduped: list[str] = []
    for attr_match in _ATTR_RE.finditer(attrs_str):
        attr = attr_match.group(1)
        name = attr.strip().split("=", 1)[0].strip().lower()
        if name in seen:
            continue
        seen.add(name)
        deduped.append(attr)

    clean_tag = prefix + "".join(deduped) + close
    return raw[: match.start()] + clean_tag + raw[match.end() :]


def _sanitize_element(element: ET.Element) -> None:
    tag = _local_name(element.tag)
    tag_key = tag.lower()
    if tag_key in BANNED_TAGS:
        raise SvgSanitizationError(f"banned SVG tag: {tag}")
    if tag not in ALLOWED_TAGS:
        raise SvgSanitizationError(f"unsupported SVG tag: {tag}")

    for raw_attr, value in list(element.attrib.items()):
        attr = _normalized_attr_name(raw_attr)
        attr_key = attr.lower()
        value_text = str(value)
        if attr_key.startswith("on"):
            raise SvgSanitizationError(f"unsafe SVG event handler: {attr}")
        if attr_key in URL_ATTRS:
            _reject_unsafe_url(value_text, attr_name=attr)
        if attr_key == "style" and "url(" in value_text.lower():
            raise SvgSanitizationError("unsafe SVG style url(...)")
        if "javascript:" in value_text.lower():
            raise SvgSanitizationError(f"unsafe javascript URL in {attr}")

    for child in list(element):
        _sanitize_element(child)


def sanitize_svg(svg_content: str) -> str:
    """Parse and validate model-generated SVG before it reaches rendering."""
    svg_content = _dedupe_svg_opening_tag(svg_content)
    try:
        root = ET.fromstring(svg_content.strip())
    except ET.ParseError as exc:
        raise SvgSanitizationError(f"SVG is not valid XML: {exc}") from exc

    if _local_name(root.tag) != "svg":
        raise SvgSanitizationError("SVG root must be <svg>")

    _sanitize_element(root)
    root.set("viewBox", "0 0 600 400")
    root.set("xmlns", SVG_NS)
    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="unicode", short_empty_elements=True)
