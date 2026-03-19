from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import GenerationMode


class GenerationRequest(BaseModel):
    subject: str
    context: str
    mode: GenerationMode = GenerationMode.BALANCED
    template_id: str
    preset_id: str
    section_count: int = Field(default=4, ge=1, le=12)


class EnhanceGenerationRequest(BaseModel):
    mode: GenerationMode = GenerationMode.BALANCED
    note: str = ""


class GenerationAcceptedResponse(BaseModel):
    generation_id: str
    status: str
    mode: GenerationMode
    source_generation_id: str | None = None
    events_url: str
    document_url: str
