from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from pipeline.types.requests import GenerationMode as PipelineMode
from pipeline.types.requests import PipelineRequest as PipelineCommand
from pipeline.types.section_content import SectionContent

GradeBand = Literal["primary", "secondary", "advanced"]


class PipelineIssue(BaseModel):
    block: str
    severity: Literal["blocking", "warning"]
    message: str


class PipelineSectionReport(BaseModel):
    section_id: str
    passed: bool
    issues: list[PipelineIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PipelineErrorInfo(BaseModel):
    node: str
    message: str
    section_id: str | None = None
    recoverable: bool = True


class PipelineDocument(BaseModel):
    generation_id: str
    subject: str
    context: str
    mode: PipelineMode
    template_id: str
    preset_id: str
    source_generation_id: str | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    sections: list[SectionContent] = Field(default_factory=list)
    qc_reports: list[PipelineSectionReport] = Field(default_factory=list)
    quality_passed: bool | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @field_validator("created_at", "updated_at", "completed_at", mode="before")
    @classmethod
    def _normalize_utc(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PipelineResult(BaseModel):
    document: PipelineDocument
    completed_nodes: list[str] = Field(default_factory=list)
    errors: list[PipelineErrorInfo] = Field(default_factory=list)
    generation_time_seconds: float


__all__ = [
    "GradeBand",
    "PipelineCommand",
    "PipelineDocument",
    "PipelineErrorInfo",
    "PipelineIssue",
    "PipelineMode",
    "PipelineResult",
    "PipelineSectionReport",
]
