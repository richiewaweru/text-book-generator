"""
pipeline.events

Typed pipeline event models plus a compatibility bridge to the shared core bus.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

import core.events as core_events
from pipeline.api import PipelineSectionReport
from pipeline.state import NodeFailureDetail
from pipeline.types.section_content import SectionContent


class PipelineStartEvent(BaseModel):
    type: Literal["pipeline_start"] = "pipeline_start"
    generation_id: str
    section_count: int
    template_id: str
    preset_id: str
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionStartedEvent(BaseModel):
    type: Literal["section_started"] = "section_started"
    generation_id: str
    section_id: str
    title: str
    position: int


class SectionReadyEvent(BaseModel):
    type: Literal["section_ready"] = "section_ready"
    generation_id: str
    section_id: str
    section: SectionContent
    completed_sections: int
    total_sections: int


class QCCompleteEvent(BaseModel):
    type: Literal["qc_complete"] = "qc_complete"
    generation_id: str
    passed: int
    total: int


class CompleteEvent(BaseModel):
    type: Literal["complete"] = "complete"
    generation_id: str
    document_url: str | None = None
    report_url: str | None = None
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    generation_id: str
    message: str
    report_url: str | None = None
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionAttemptStartedEvent(BaseModel):
    type: Literal["section_attempt_started"] = "section_attempt_started"
    generation_id: str
    section_id: str
    attempt: int
    trigger: Literal["initial", "rerender"]
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class NodeStartedEvent(BaseModel):
    type: Literal["node_started"] = "node_started"
    generation_id: str
    node: str
    attempt: int | None = None
    section_id: str | None = None
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class NodeFinishedEvent(BaseModel):
    type: Literal["node_finished"] = "node_finished"
    generation_id: str
    node: str
    status: Literal["succeeded", "failed"]
    attempt: int | None = None
    section_id: str | None = None
    latency_ms: float | None = None
    error: str | None = None
    finished_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionReportUpdatedEvent(BaseModel):
    type: Literal["section_report_updated"] = "section_report_updated"
    generation_id: str
    section_id: str
    source: Literal["assembler", "qc_agent"]
    report: PipelineSectionReport
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionRetryQueuedEvent(BaseModel):
    type: Literal["section_retry_queued"] = "section_retry_queued"
    generation_id: str
    section_id: str
    reason: str
    block_type: str
    next_attempt: int
    max_attempts: int
    queued_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SectionFailedEvent(BaseModel):
    type: Literal["section_failed"] = "section_failed"
    generation_id: str
    section_id: str
    title: str
    position: int
    failed_at_node: str
    error_type: str
    error_summary: str
    focus: str | None = None
    bridges_from: str | None = None
    bridges_to: str | None = None
    needs_diagram: bool = False
    needs_worked_example: bool = False
    attempt_count: int = 0
    can_retry: bool = False
    missing_components: list[str] = Field(default_factory=list)
    failure_detail: NodeFailureDetail | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ValidationRepairAttemptedEvent(BaseModel):
    type: Literal["validation_repair_attempted"] = "validation_repair_attempted"
    generation_id: str
    section_id: str
    node: str = "content_generator"
    attempt: int = 1
    error_summary: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ValidationRepairSucceededEvent(BaseModel):
    type: Literal["validation_repair_succeeded"] = "validation_repair_succeeded"
    generation_id: str
    section_id: str
    node: str = "content_generator"
    attempt: int = 1
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DiagramOutcomeEvent(BaseModel):
    type: Literal["diagram_outcome"] = "diagram_outcome"
    generation_id: str
    section_id: str
    outcome: Literal["success", "timeout", "error", "skipped"]
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


LLMCallStartedEvent = core_events.LLMCallStartedEvent
LLMCallSucceededEvent = core_events.LLMCallSucceededEvent
LLMCallFailedEvent = core_events.LLMCallFailedEvent

PipelineEvent = (
    PipelineStartEvent
    | SectionStartedEvent
    | SectionReadyEvent
    | QCCompleteEvent
    | CompleteEvent
    | ErrorEvent
    | LLMCallStartedEvent
    | LLMCallSucceededEvent
    | LLMCallFailedEvent
    | SectionAttemptStartedEvent
    | NodeStartedEvent
    | NodeFinishedEvent
    | SectionReportUpdatedEvent
    | SectionRetryQueuedEvent
    | SectionFailedEvent
    | ValidationRepairAttemptedEvent
    | ValidationRepairSucceededEvent
    | DiagramOutcomeEvent
)


PipelineEventBus = core_events.EventBus
event_bus = core_events.event_bus


__all__ = [
    "CompleteEvent",
    "ErrorEvent",
    "PipelineEvent",
    "PipelineEventBus",
    "PipelineStartEvent",
    "QCCompleteEvent",
    "SectionReadyEvent",
    "SectionStartedEvent",
    "SectionAttemptStartedEvent",
    "SectionFailedEvent",
    "NodeStartedEvent",
    "NodeFinishedEvent",
    "SectionReportUpdatedEvent",
    "SectionRetryQueuedEvent",
    "ValidationRepairAttemptedEvent",
    "ValidationRepairSucceededEvent",
    "DiagramOutcomeEvent",
    "PipelineEventBus",
    "event_bus",
    "LLMCallStartedEvent",
    "LLMCallSucceededEvent",
    "LLMCallFailedEvent",
]
