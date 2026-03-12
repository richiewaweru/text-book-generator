from pydantic import BaseModel

from textbook_agent.domain.entities.quality_report import QualityReport
from textbook_agent.domain.value_objects import Depth, NotationLanguage


class GenerationRequest(BaseModel):
    """Request DTO for textbook generation.

    Only per-generation fields live here. Student-level context
    (age, education_level, interests, etc.) comes from the
    persistent StudentProfile and is merged in the use case.
    """

    subject: str
    context: str
    depth: Depth | None = None
    language: NotationLanguage | None = None
    provider: str = "claude"


class GenerationResponse(BaseModel):
    """Response DTO for textbook generation."""

    textbook_id: str
    output_path: str
    quality_report: QualityReport | None = None
    generation_time_seconds: float
    quality_reruns: int = 0
