from pydantic import BaseModel, Field


class GenerationAcceptedResponse(BaseModel):
    generation_id: str
    status: str
    events_url: str
    document_url: str
    report_url: str
    section_count: int = 0
    sections_with_visuals: int = 0
    subtopics_covered: list[str] = Field(default_factory=list)
    warning: str | None = None
