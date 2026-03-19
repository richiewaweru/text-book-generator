"""
pipeline.events

Typed event models plus a simple in-process pub/sub bus for SSE streaming.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from pipeline.types.section_content import SectionContent


class PipelineStartEvent(BaseModel):
    type: Literal["pipeline_start"] = "pipeline_start"
    generation_id: str
    section_count: int
    template_id: str
    preset_id: str
    mode: str
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
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    generation_id: str
    message: str
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── LLM diagnostics (best-effort; emitted for every LLM agent call) ─────────


class LLMCallStartedEvent(BaseModel):
    type: Literal["llm_call_started"] = "llm_call_started"
    generation_id: str
    node: str
    route: str
    provider: str | None = None
    model_name: str | None = None
    attempt: int
    section_id: str | None = None


class LLMCallSucceededEvent(BaseModel):
    type: Literal["llm_call_succeeded"] = "llm_call_succeeded"
    generation_id: str
    node: str
    route: str
    provider: str | None = None
    model_name: str | None = None
    attempt: int
    section_id: str | None = None
    latency_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None


class LLMCallFailedEvent(BaseModel):
    type: Literal["llm_call_failed"] = "llm_call_failed"
    generation_id: str
    node: str
    route: str
    provider: str | None = None
    model_name: str | None = None
    attempt: int
    section_id: str | None = None
    latency_ms: float | None = None
    retryable: bool = True
    error: str


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
)


class PipelineEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, generation_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[generation_id].append(queue)
        return queue

    def publish(self, generation_id: str, event: PipelineEvent | dict) -> None:
        payload = (
            event.model_dump(mode="json", exclude_none=True)
            if hasattr(event, "model_dump")
            else event
        )
        for queue in self._subscribers.get(generation_id, []):
            queue.put_nowait(payload)

    def unsubscribe(self, generation_id: str, queue: asyncio.Queue) -> None:
        queues = self._subscribers.get(generation_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues and generation_id in self._subscribers:
            del self._subscribers[generation_id]


event_bus = PipelineEventBus()


__all__ = [
    "CompleteEvent",
    "ErrorEvent",
    "PipelineEvent",
    "PipelineEventBus",
    "PipelineStartEvent",
    "QCCompleteEvent",
    "SectionReadyEvent",
    "SectionStartedEvent",
    "event_bus",
    "LLMCallStartedEvent",
    "LLMCallSucceededEvent",
    "LLMCallFailedEvent",
]
