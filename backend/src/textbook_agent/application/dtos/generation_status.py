from pydantic import BaseModel, Field

from pipeline.api import PipelineDocument
from textbook_agent.domain.value_objects import GenerationMode


class GenerationHistoryItem(BaseModel):
    id: str
    subject: str
    status: str
    mode: GenerationMode
    source_generation_id: str | None = None
    error_type: str | None = None
    error_code: str | None = None
    requested_template_id: str
    resolved_template_id: str | None = None
    requested_preset_id: str
    resolved_preset_id: str | None = None
    quality_passed: bool | None = None
    generation_time_seconds: float | None = None
    created_at: str | None = None
    completed_at: str | None = None


class GenerationDetail(BaseModel):
    id: str
    subject: str
    context: str
    status: str
    mode: GenerationMode
    source_generation_id: str | None = None
    error: str | None = None
    error_type: str | None = None
    error_code: str | None = None
    requested_template_id: str
    resolved_template_id: str | None = None
    requested_preset_id: str
    resolved_preset_id: str | None = None
    quality_passed: bool | None = None
    generation_time_seconds: float | None = None
    created_at: str | None = None
    completed_at: str | None = None
    document_path: str | None = None


class GenerationListResponse(BaseModel):
    items: list[GenerationHistoryItem] = Field(default_factory=list)


class GenerationDocumentResponse(BaseModel):
    document: PipelineDocument
