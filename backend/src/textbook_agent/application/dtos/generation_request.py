from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import Depth, NotationLanguage
from textbook_agent.domain.entities.quality_report import QualityReport


class GenerationRequest(BaseModel):
    """Request DTO for textbook generation."""

    subject: str
    age: int = Field(ge=8, le=99)
    context: str
    depth: Depth = Depth.STANDARD
    language: NotationLanguage = NotationLanguage.PLAIN
    provider: str = "claude"


class GenerationResponse(BaseModel):
    """Response DTO for textbook generation."""

    textbook_id: str
    output_path: str
    quality_report: QualityReport | None = None
    generation_time_seconds: float
