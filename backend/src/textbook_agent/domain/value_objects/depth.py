from enum import Enum


class Depth(str, Enum):
    """Controls section depth and number of worked examples."""

    SURVEY = "survey"
    STANDARD = "standard"
    DEEP = "deep"
