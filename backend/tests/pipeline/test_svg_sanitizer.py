from __future__ import annotations

import pytest

from pipeline.media.svg_sanitizer import (
    SvgSanitizationError,
    _dedupe_svg_opening_tag,
    sanitize_svg,
)


def test_sanitize_svg_accepts_safe_svg_and_enforces_viewbox() -> None:
    svg = sanitize_svg('<svg><line x1="0" y1="0" x2="10" y2="10" /><text>rise</text></svg>')

    assert 'viewBox="0 0 600 400"' in svg
    assert "<line" in svg
    assert "<text" in svg


def test_sanitize_svg_dedupes_duplicate_xmlns_before_parse() -> None:
    svg = sanitize_svg(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns="duplicate">'
        '<line x1="0" y1="0" x2="10" y2="10" /><text>rise</text></svg>'
    )

    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "duplicate" not in svg
    assert "<line" in svg


def test_dedupe_svg_opening_tag_keeps_first_viewbox() -> None:
    svg = _dedupe_svg_opening_tag(
        '<svg viewBox="0 0 600 400" viewBox="0 0 10 10"><line /></svg>'
    )

    assert 'viewBox="0 0 600 400"' in svg
    assert 'viewBox="0 0 10 10"' not in svg


def test_dedupe_svg_opening_tag_leaves_valid_svg_unchanged() -> None:
    svg = '<svg viewBox="0 0 600 400" role="img"><line /></svg>'

    assert _dedupe_svg_opening_tag(svg) == svg


def test_dedupe_svg_opening_tag_leaves_non_svg_text_unchanged() -> None:
    text = "<div><line /></div>"

    assert _dedupe_svg_opening_tag(text) == text


@pytest.mark.parametrize(
    "svg",
    [
        "<svg><script>alert(1)</script></svg>",
        '<svg><foreignObject><p>bad</p></foreignObject></svg>',
        '<svg><image href="https://example.com/a.png" /></svg>',
    ],
)
def test_sanitize_svg_rejects_banned_tags(svg: str) -> None:
    with pytest.raises(SvgSanitizationError):
        sanitize_svg(svg)


@pytest.mark.parametrize(
    "svg",
    [
        '<svg onload="alert(1)"><line /></svg>',
        '<svg><a href="https://example.com"><text>bad</text></a></svg>',
        '<svg><path href="javascript:alert(1)" /></svg>',
        '<svg><rect style="fill:url(https://example.com/pattern)" /></svg>',
    ],
)
def test_sanitize_svg_rejects_unsafe_attributes(svg: str) -> None:
    with pytest.raises(SvgSanitizationError):
        sanitize_svg(svg)


def test_sanitize_svg_rejects_non_svg_root() -> None:
    with pytest.raises(SvgSanitizationError, match="root"):
        sanitize_svg("<div></div>")
