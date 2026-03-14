from dataclasses import dataclass


@dataclass(frozen=True)
class ModelRouting:
    """Per-task model routing for a single generation run."""

    planner: str | None = None
    content: str | None = None
    diagram: str | None = None
    code: str | None = None
    inline_quality: str | None = None
    final_quality: str | None = None
