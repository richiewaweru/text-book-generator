from __future__ import annotations

import pytest

from v3_execution.runtime.progress import titled_label


@pytest.mark.parametrize(
    ("prefix", "title", "fallback", "expected"),
    [
        ("Writing", "Introducing the concept", "Generating section", "Writing: Introducing the concept"),
        ("Repairing", "", "Repairing section", "Repairing section"),
        ("Creating diagram for", "Practice problems", "Creating diagram", "Creating diagram for: Practice problems"),
    ],
)
def test_titled_label(prefix: str, title: str, fallback: str, expected: str) -> None:
    assert titled_label(prefix, title, fallback=fallback) == expected
