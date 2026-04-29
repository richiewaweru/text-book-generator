from __future__ import annotations

import pytest

from pipeline.media.svg_validator import (
    SvgIntentValidationError,
    SvgValidationError,
    validate_svg_basic,
    validate_svg_intent,
)


def test_validate_svg_basic_accepts_visible_svg() -> None:
    validate_svg_basic(
        '<svg viewBox="0 0 600 400"><line x1="0" y1="0" x2="10" y2="10" /></svg>'
    )


def test_validate_svg_basic_rejects_empty_svg() -> None:
    with pytest.raises(SvgValidationError, match="no visible"):
        validate_svg_basic('<svg viewBox="0 0 600 400"></svg>')


def test_validate_svg_basic_rejects_missing_viewbox() -> None:
    with pytest.raises(SvgValidationError, match="viewBox"):
        validate_svg_basic("<svg><line /></svg>")


def test_validate_svg_basic_rejects_oversized_svg() -> None:
    with pytest.raises(SvgValidationError, match="too large"):
        validate_svg_basic('<svg viewBox="0 0 600 400">' + (" " * 50_001) + "<line /></svg>")


def test_validate_svg_intent_accepts_slope_graph() -> None:
    validate_svg_intent(
        '<svg viewBox="0 0 600 400"><line x1="50" y1="350" x2="550" y2="50" />'
        '<text x="90" y="90">rise 3</text></svg>',
        "Draw a coordinate grid with a line showing slope 3.",
    )


def test_validate_svg_intent_rejects_flowchart_for_slope() -> None:
    with pytest.raises(SvgIntentValidationError, match="flowchart"):
        validate_svg_intent(
            '<svg viewBox="0 0 600 400"><rect /><rect /><rect />'
            '<line x1="0" y1="0" x2="10" y2="10" /><text>Step</text></svg>',
            "Produce a line showing a slope of 3.",
        )
