from enum import Enum


class GenerationMode(str, Enum):
    """Controls the speed/quality tradeoff for a generation run."""

    DRAFT = "draft"
    BALANCED = "balanced"
    STRICT = "strict"
