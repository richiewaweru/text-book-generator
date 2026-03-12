from typing import Literal

from pydantic import BaseModel

from .generation_request import GenerationResponse


class GenerationProgress(BaseModel):
    """Progress information for an ongoing generation."""

    current_node: str
    completed_nodes: list[str]
    total_nodes: int


class GenerationStatus(BaseModel):
    """Full status of a generation job."""

    id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: GenerationProgress | None = None
    result: GenerationResponse | None = None
    error: str | None = None
    error_type: str | None = None
