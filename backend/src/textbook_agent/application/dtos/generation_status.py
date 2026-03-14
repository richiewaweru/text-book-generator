from typing import Literal

from pydantic import BaseModel, Field

from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.value_objects import GenerationMode

from .generation_request import GenerationResponse


class GenerationProgress(BaseModel):
    """Progress information for an ongoing generation."""

    mode: GenerationMode
    phase: Literal["planning", "generating", "checking", "fixing", "rendering"]
    message: str
    sections_total: int | None = None
    sections_completed: int = 0
    current_section_id: str | None = None
    current_section_title: str | None = None
    retry_attempt: int | None = None
    retry_limit: int | None = None
    flagged_section_ids: list[str] = Field(default_factory=list)


class GenerationResultSummary(BaseModel):
    """Public summary of a completed generation returned by status endpoints."""

    textbook_id: str
    mode: GenerationMode
    quality_report: QualityReport | None = None
    generation_time_seconds: float
    quality_reruns: int = 0
    source_generation_id: str | None = None

    @classmethod
    def from_response(cls, response: GenerationResponse) -> "GenerationResultSummary":
        return cls(
            textbook_id=response.textbook_id,
            mode=response.mode,
            quality_report=response.quality_report,
            generation_time_seconds=response.generation_time_seconds,
            quality_reruns=response.quality_reruns,
            source_generation_id=response.source_generation_id,
        )


class GenerationStatus(BaseModel):
    """Full status of a generation job."""

    id: str
    status: Literal["pending", "running", "completed", "failed"]
    mode: GenerationMode | None = None
    progress: GenerationProgress | None = None
    result: GenerationResultSummary | None = None
    error: str | None = None
    error_type: str | None = None
    source_generation_id: str | None = None
