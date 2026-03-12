from typing import Literal

from pydantic import BaseModel

from textbook_agent.domain.entities.quality_report import QualityReport

from .generation_request import GenerationResponse


class GenerationProgress(BaseModel):
    """Progress information for an ongoing generation."""

    current_node: str
    completed_nodes: list[str]
    total_nodes: int


class GenerationResultSummary(BaseModel):
    """Public summary of a completed generation returned by status endpoints."""

    textbook_id: str
    quality_report: QualityReport | None = None
    generation_time_seconds: float
    quality_reruns: int = 0

    @classmethod
    def from_response(cls, response: GenerationResponse) -> "GenerationResultSummary":
        return cls(
            textbook_id=response.textbook_id,
            quality_report=response.quality_report,
            generation_time_seconds=response.generation_time_seconds,
            quality_reruns=response.quality_reruns,
        )


class GenerationStatus(BaseModel):
    """Full status of a generation job."""

    id: str
    status: Literal["pending", "running", "completed", "failed"]
    progress: GenerationProgress | None = None
    result: GenerationResultSummary | None = None
    error: str | None = None
    error_type: str | None = None
