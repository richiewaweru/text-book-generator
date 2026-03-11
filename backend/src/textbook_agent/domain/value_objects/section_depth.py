from enum import Enum


class SectionDepth(str, Enum):
    """Estimated depth for a single section."""

    LIGHT = "light"
    MEDIUM = "medium"
    DEEP = "deep"
