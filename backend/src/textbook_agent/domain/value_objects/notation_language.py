from enum import Enum


class NotationLanguage(str, Enum):
    """Preferred notation style for the textbook."""

    PLAIN = "plain"
    MATH_NOTATION = "math_notation"
    PYTHON = "python"
    PSEUDOCODE = "pseudocode"
