from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from pipeline.api import PipelineDocument, PipelineSectionReport
from pipeline.contracts import get_optional_fields, get_required_fields
import core.events as core_events
from pipeline.reporting import (
    GenerationReport,
    GenerationReportLLMAttempt,
    GenerationReportNode,
    GenerationReportRetry,
    GenerationReportSection,
    GenerationReportSummary,
    GenerationTimelineEvent,
)
from telemetry.ports.generation_report_repository import GenerationReportRepository

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class GenerationReportRecorder:
    def __init__(
        self,
        *,
        generation: Any,
        repository: GenerationReportRepository,
    ) -> None:
        expected_components = sorted(
            set(
                get_required_fields(generation.requested_template_id)
                + get_optional_fields(generation.requested_template_id)
            )
        )
        self._repository = repository
        self._generation = generation
        self._expected_components = expected_components
        self._report = GenerationReport(
            generation_id=generation.id,
            subject=generation.subject,
            context=generation.context,
            template_id=generation.requested_template_id,
            preset_id=generation.requested_preset_id,
            status="running",
            section_count=generation.section_count,
            started_at=generation.created_at,
            summary=GenerationReportSummary(),
        )
        self._sections: dict[str, GenerationReportSection] = {}
        self._generation_nodes: dict[tuple[str, int | None], GenerationReportNode] = {}
        self._section_nodes: dict[tuple[str, str, int | None], GenerationReportNode] = {}
        self._timeline_sequence = 0
        self._queue: asyncio.Queue | None = None
        self._consumer: asyncio.Task | None = None
        self._consumer_error: Exception | None = None
        self._consumer_dead = False
        self._dropped_event_count = 0

    @property
    def report(self) -> GenerationReport:
        return self._report

    @property
    def consumer_error(self) -> Exception | None:
        return self._consumer_error

    @property
    def consumer_dead(self) -> bool:
        return self._consumer_dead

    @property
    def dropped_event_count(self) -> int:
        return self._dropped_event_count

    @property
    def diagnostics_degraded(self) -> bool:
        return (
            self._consumer_error is not None
            or self._consumer_dead
            or self._dropped_event_count > 0
        )

    async def start(self) -> None:
        self._queue = core_events.event_bus.subscribe(self._generation.id)
        await self._persist()
        self._consumer = asyncio.create_task(self._consume_events())

    async def stop(self) -> None:
        if self._consumer is not None:
            self._consumer.cancel()
            with suppress(asyncio.CancelledError):
                await self._consumer
        if self._queue is not None:
            self._drain_queue(mark_dead=False)
            core_events.event_bus.unsubscribe(self._generation.id, self._queue)
            self._queue = None
        self._consumer = None

    async def wait_for_idle(self, *, timeout: float = 5.0) -> None:
        if self._queue is None:
            return
        if self._consumer is not None and self._consumer.done():
            self._consumer_dead = True
            with suppress(asyncio.CancelledError, asyncio.InvalidStateError):
                exc = self._consumer.exception()
                if exc is not None:
                    self._consumer_error = self._consumer_error or exc
            self._drain_queue()
            return
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except (TimeoutError, asyncio.TimeoutError):
            logger.warning(
                "Recorder wait_for_idle timed out after %.1fs for generation=%s",
                timeout,
                self._generation.id,
            )
            self._drain_queue()

    async def finalize_success(
        self,
        *,
        document: PipelineDocument,
        generation_time_seconds: float | None,
    ) -> None:
        self._apply_success_state(
            document=document,
            generation_time_seconds=generation_time_seconds,
        )
        await self._persist()

    async def finalize_failure(
        self,
        *,
        error: str,
        generation_time_seconds: float | None = None,
    ) -> None:
        self._apply_failure_state(
            error=error,
            generation_time_seconds=generation_time_seconds,
        )
        await self._persist()

    def build_success_snapshot(
        self,
        *,
        document: PipelineDocument,
        generation_time_seconds: float | None,
    ) -> GenerationReport:
        self._apply_success_state(
            document=document,
            generation_time_seconds=generation_time_seconds,
        )
        self._sync_views()
        return self._report.model_copy(deep=True)

    def build_failure_snapshot(
        self,
        *,
        error: str,
        generation_time_seconds: float | None = None,
    ) -> GenerationReport:
        self._apply_failure_state(
            error=error,
            generation_time_seconds=generation_time_seconds,
        )
        self._sync_views()
        return self._report.model_copy(deep=True)

    def log_final_summary(self) -> None:
        self._log_final_summary()

    async def apply_event(self, event: Any) -> None:
        payload = self._payload(event)
        self._append_timeline(payload)

        event_type = payload.get("type")
        if event_type == "pipeline_start":
            self._handle_pipeline_start(payload)
        elif event_type == "section_started":
            self._handle_section_started(payload)
        elif event_type == "section_partial":
            self._handle_section_partial(payload)
        elif event_type == "section_asset_pending":
            self._handle_section_asset_pending(payload)
        elif event_type == "section_asset_ready":
            self._handle_section_asset_ready(payload)
        elif event_type == "section_final":
            self._handle_section_final(payload)
        elif event_type == "section_attempt_started":
            self._handle_section_attempt_started(payload)
        elif event_type == "node_started":
            self._handle_node_started(payload)
        elif event_type == "node_finished":
            self._handle_node_finished(payload)
        elif event_type == "llm_call_started":
            self._handle_llm_started(payload)
        elif event_type == "llm_call_succeeded":
            self._handle_llm_succeeded(payload)
        elif event_type == "llm_call_failed":
            self._handle_llm_failed(payload)
        elif event_type == "section_report_updated":
            self._handle_section_report_updated(payload)
        elif event_type == "section_retry_queued":
            self._handle_section_retry_queued(payload)
        elif event_type == "section_failed":
            self._handle_section_failed(payload)
        elif event_type == "validation_repair_attempted":
            self._handle_validation_repair_attempted(payload)
        elif event_type == "validation_repair_succeeded":
            self._handle_validation_repair_succeeded(payload)
        elif event_type == "diagram_outcome":
            self._handle_diagram_outcome(payload)
        elif event_type == "section_ready":
            self._handle_section_ready(payload)
        elif event_type == "complete":
            self._handle_complete(payload)
        elif event_type == "error":
            self._handle_error(payload)

        self._refresh_summary()
        await self._persist()
        self._log_event(payload)

    async def _consume_events(self) -> None:
        assert self._queue is not None
        try:
            while True:
                event = await self._queue.get()
                try:
                    await self.apply_event(event)
                except Exception as exc:
                    self._consumer_error = exc
                    logger.exception(
                        "Recorder failed to process event for generation=%s type=%s",
                        self._generation.id,
                        event.get("type", "unknown") if isinstance(event, dict) else "unknown",
                    )
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._consumer_dead = True
            self._consumer_error = exc
            logger.exception(
                "Recorder consumer crashed for generation=%s",
                self._generation.id,
            )
            raise

    def _payload(self, event: Any) -> dict[str, Any]:
        if hasattr(event, "model_dump"):
            return event.model_dump(mode="json", exclude_none=True)
        return dict(event)

    def _trace_id(self, payload: dict[str, Any]) -> str | None:
        return payload.get("trace_id") or payload.get("generation_id")

    def _caller(self, payload: dict[str, Any]) -> str | None:
        return payload.get("caller") or payload.get("node")

    def _event_timestamp(self, payload: dict[str, Any]) -> datetime:
        for key in (
            "started_at",
            "finished_at",
            "updated_at",
            "queued_at",
            "completed_at",
            "timestamp",
        ):
            if key in payload:
                parsed = _as_utc(payload[key])
                if parsed is not None:
                    return parsed
        return _utc_now()

    def _append_timeline(self, payload: dict[str, Any]) -> None:
        self._timeline_sequence += 1
        self._report.timeline.append(
            GenerationTimelineEvent(
                sequence=self._timeline_sequence,
                type=payload.get("type", "unknown"),
                timestamp=self._event_timestamp(payload),
                node=self._caller(payload) or payload.get("node"),
                section_id=payload.get("section_id"),
                attempt=payload.get("attempt"),
                payload=payload,
            )
        )

    def _ensure_section(self, section_id: str) -> GenerationReportSection:
        if section_id not in self._sections:
            self._sections[section_id] = GenerationReportSection(
                section_id=section_id,
                expected_components=list(self._expected_components),
                missing_components=list(self._expected_components),
            )
        return self._sections[section_id]

    def _ensure_node(
        self,
        *,
        node: str,
        section_id: str | None,
        attempt: int | None,
    ) -> GenerationReportNode:
        if section_id is None:
            key = (node, attempt)
            node_report = self._generation_nodes.get(key)
            if node_report is None:
                node_report = GenerationReportNode(
                    node=node,
                    scope="generation",
                    attempt=attempt,
                )
                self._generation_nodes[key] = node_report
            return node_report

        key = (section_id, node, attempt)
        node_report = self._section_nodes.get(key)
        if node_report is None:
            node_report = GenerationReportNode(
                node=node,
                scope="section",
                attempt=attempt,
            )
            self._section_nodes[key] = node_report
        return node_report

    def _handle_pipeline_start(self, payload: dict[str, Any]) -> None:
        self._report.status = "running"
        self._report.section_count = payload.get("section_count", self._report.section_count)
        self._report.started_at = _as_utc(payload.get("started_at")) or self._report.started_at

    def _handle_section_started(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.title = payload.get("title", section.title)
        section.position = payload.get("position", section.position)
        if section.status == "stalled":
            section.status = "planned"

    def _handle_section_partial(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "running"
        section.completed_at = None
        partial_payload = payload.get("section", {})
        delivered = self._delivered_components(partial_payload)
        section.delivered_components = delivered
        section.missing_components = [
            component for component in section.expected_components if component not in delivered
        ]
        section.final_error = None
        section.failure_detail = None

    def _handle_section_asset_pending(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "running"
        pending_assets = list(payload.get("pending_assets", []))
        for asset in pending_assets:
            if asset not in section.missing_components:
                section.missing_components.append(asset)
        section.missing_components.sort()

    def _handle_section_asset_ready(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "running"
        pending_assets = set(payload.get("pending_assets", []))
        section.missing_components = [
            component
            for component in section.missing_components
            if component in pending_assets or component not in payload.get("ready_assets", [])
        ]

    def _handle_section_attempt_started(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.attempt_count = max(section.attempt_count, payload.get("attempt", 0))
        section.current_attempt = payload.get("attempt")
        section.status = "running"
        section.first_started_at = (
            _as_utc(payload.get("started_at")) or section.first_started_at or _utc_now()
        )

    def _handle_node_started(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        node = self._ensure_node(
            node=payload["node"],
            section_id=section_id,
            attempt=payload.get("attempt"),
        )
        node.status = "running"
        node.started_at = _as_utc(payload.get("started_at")) or _utc_now()
        if section_id:
            section = self._ensure_section(section_id)
            section.status = "running"
            section.current_attempt = payload.get("attempt", section.current_attempt)
            if section.first_started_at is None:
                section.first_started_at = node.started_at

    def _handle_node_finished(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        node = self._ensure_node(
            node=payload["node"],
            section_id=section_id,
            attempt=payload.get("attempt"),
        )
        node.status = payload.get("status", node.status)
        node.completed_at = _as_utc(payload.get("finished_at")) or _utc_now()
        node.latency_ms = payload.get("latency_ms")
        node.error = payload.get("error")
        if section_id and payload.get("status") == "failed":
            section = self._ensure_section(section_id)
            section.final_error = payload.get("error", section.final_error)
            if section.status != "ready":
                section.status = "failed"

    def _handle_llm_started(self, payload: dict[str, Any]) -> None:
        llm = self._ensure_llm_attempt(payload)
        llm.status = "started"
        llm.started_at = _utc_now()

    def _handle_llm_succeeded(self, payload: dict[str, Any]) -> None:
        llm = self._ensure_llm_attempt(payload)
        llm.status = "succeeded"
        llm.completed_at = _utc_now()
        llm.latency_ms = payload.get("latency_ms")
        llm.tokens_in = payload.get("tokens_in")
        llm.tokens_out = payload.get("tokens_out")
        llm.cost_usd = payload.get("cost_usd")

    def _handle_llm_failed(self, payload: dict[str, Any]) -> None:
        llm = self._ensure_llm_attempt(payload)
        llm.status = "failed"
        llm.completed_at = _utc_now()
        llm.latency_ms = payload.get("latency_ms")
        llm.retryable = payload.get("retryable")
        llm.error = payload.get("error")

    def _ensure_llm_attempt(self, payload: dict[str, Any]) -> GenerationReportLLMAttempt:
        parent = self._llm_parent_node(payload)
        for llm_call in parent.llm_calls:
            if llm_call.attempt == payload["attempt"]:
                return llm_call

        llm_call = GenerationReportLLMAttempt(
            node=self._caller(payload) or payload.get("node", ""),
            attempt=payload["attempt"],
            slot=payload["slot"],
            family=payload.get("family"),
            model_name=payload.get("model_name"),
            endpoint_host=payload.get("endpoint_host"),
        )
        parent.llm_calls.append(llm_call)
        return llm_call

    def _llm_parent_node(self, payload: dict[str, Any]) -> GenerationReportNode:
        section_id = payload.get("section_id")
        node_name = self._caller(payload) or payload["node"]
        if section_id:
            section = self._ensure_section(section_id)
            return self._ensure_node(
                node=node_name,
                section_id=section_id,
                attempt=section.current_attempt,
            )

        generation_candidates = [
            node
            for (name, _attempt), node in self._generation_nodes.items()
            if name == node_name
        ]
        if generation_candidates:
            generation_candidates.sort(key=lambda item: item.attempt or 0, reverse=True)
            return generation_candidates[0]
        return self._ensure_node(node=node_name, section_id=None, attempt=1)

    def _handle_section_report_updated(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        report = PipelineSectionReport.model_validate(payload["report"])
        section.warnings = list(report.warnings)
        section.issues = list(report.issues)

    def _handle_section_retry_queued(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "retry_queued"
        section.queued_retries.append(
            GenerationReportRetry(
                reason=payload["reason"],
                block_type=payload["block_type"],
                next_attempt=payload["next_attempt"],
                max_attempts=payload["max_attempts"],
                queued_at=_as_utc(payload.get("queued_at")) or _utc_now(),
            )
        )

    def _handle_section_failed(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.title = payload.get("title", section.title)
        section.position = payload.get("position", section.position)
        section.status = "failed"
        section.final_error = payload.get("error_summary", section.final_error)
        section.missing_components = list(payload.get("missing_components", section.missing_components))
        section.failure_detail = payload.get("failure_detail")
        section.attempt_count = max(section.attempt_count, payload.get("attempt_count", 0))

    def _handle_validation_repair_attempted(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.validation_repair_attempts += 1

    def _handle_validation_repair_succeeded(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.validation_repair_successes += 1

    def _handle_diagram_outcome(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.diagram_outcome = payload.get("outcome")

    def _handle_section_ready(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "ready"
        section.completed_at = _utc_now()
        section.final_error = None
        section.failure_detail = None
        delivered = self._delivered_components(payload.get("section", {}))
        section.delivered_components = delivered
        section.missing_components = [
            component for component in section.expected_components if component not in delivered
        ]

    def _handle_section_final(self, payload: dict[str, Any]) -> None:
        self._handle_section_ready(payload)

    def _handle_complete(self, payload: dict[str, Any]) -> None:
        self._report.status = "completed"
        self._report.completed_at = _as_utc(payload.get("completed_at")) or self._report.completed_at
        self._update_wall_time()

    def _handle_error(self, payload: dict[str, Any]) -> None:
        self._report.status = "failed"
        self._report.completed_at = _as_utc(payload.get("completed_at")) or self._report.completed_at
        self._report.final_error = payload.get("message", self._report.final_error)
        self._update_wall_time()

    def _delivered_components(self, section_payload: dict[str, Any]) -> list[str]:
        return sorted(
            component
            for component in self._expected_components
            if section_payload.get(component)
        )

    def _apply_document_snapshot(self, document: PipelineDocument) -> None:
        self._report.section_count = len(document.section_manifest) or self._report.section_count
        self._report.quality_passed = document.quality_passed

        for item in document.section_manifest:
            if isinstance(item, dict):
                section_id = item["section_id"]
                title = item.get("title")
                position = item.get("position")
            else:
                section_id = item.section_id
                title = item.title
                position = item.position
            section = self._ensure_section(section_id)
            section.title = title
            section.position = position

        for section_content in document.sections:
            section = self._ensure_section(section_content.section_id)
            payload = section_content.model_dump(exclude_none=True)
            delivered = self._delivered_components(payload)
            section.status = "ready"
            section.completed_at = document.completed_at or section.completed_at or _utc_now()
            section.delivered_components = delivered
            section.missing_components = [
                component for component in section.expected_components if component not in delivered
            ]
            section.final_error = None

        for partial_section in document.partial_sections:
            payload = (
                partial_section
                if isinstance(partial_section, dict)
                else partial_section.model_dump(exclude_none=True)
            )
            section = self._ensure_section(payload["section_id"])
            if section.status == "ready":
                continue
            section.title = payload.get("content", {}).get("header", {}).get("title", section.title)
            content = payload.get("content", {})
            delivered = self._delivered_components(content)
            section.status = "running"
            section.completed_at = None
            section.delivered_components = delivered
            section.missing_components = [
                component for component in section.expected_components if component not in delivered
            ]
            for pending_asset in payload.get("pending_assets", []):
                if pending_asset not in section.missing_components:
                    section.missing_components.append(pending_asset)
            section.missing_components.sort()
            section.final_error = None
            section.failure_detail = None

        for failed_section in document.failed_sections:
            payload = (
                failed_section
                if isinstance(failed_section, dict)
                else failed_section.model_dump(exclude_none=True)
            )
            section = self._ensure_section(payload["section_id"])
            section.title = payload.get("title", section.title)
            section.position = payload.get("position", section.position)
            section.status = "failed"
            section.final_error = payload.get("error_summary", section.final_error)
            section.failure_detail = payload.get("failure_detail")
            section.missing_components = list(payload.get("missing_components", section.missing_components))

    def _apply_success_state(
        self,
        *,
        document: PipelineDocument,
        generation_time_seconds: float | None,
    ) -> None:
        self._apply_document_snapshot(document)
        self._report.status = "completed"
        self._report.quality_passed = document.quality_passed
        self._report.generation_time_seconds = generation_time_seconds
        self._report.completed_at = document.completed_at or _utc_now()
        self._report.final_error = document.error
        self._finalize_incomplete_sections(final_status="completed")
        self._report.outcome = self._derive_outcome(final_status="completed")
        self._update_wall_time()
        self._refresh_summary()

    def _apply_failure_state(
        self,
        *,
        error: str,
        generation_time_seconds: float | None = None,
    ) -> None:
        self._report.status = "failed"
        self._report.outcome = "failed"
        self._report.quality_passed = False
        self._report.completed_at = _utc_now()
        self._report.generation_time_seconds = generation_time_seconds
        self._report.final_error = error
        self._finalize_incomplete_sections(final_status="failed")
        self._update_wall_time()
        self._refresh_summary()

    def _finalize_incomplete_sections(self, *, final_status: str) -> None:
        for section in self._sections.values():
            if section.status == "ready":
                continue
            if section.final_error:
                section.status = "failed"
            elif final_status == "failed":
                if section.status == "retry_queued" or section.attempt_count == 0:
                    section.status = "stalled"
                else:
                    section.status = "failed"
            else:
                section.status = "stalled"

    def _derive_outcome(self, *, final_status: str) -> str:
        planned = max(len(self._sections), self._report.section_count or 0)
        ready = sum(1 for section in self._sections.values() if section.status == "ready")
        if final_status == "failed":
            return "failed"
        return "full" if planned == ready else "partial"

    def _update_wall_time(self) -> None:
        if self._report.started_at and self._report.completed_at:
            self._report.wall_time_seconds = (
                self._report.completed_at - self._report.started_at
            ).total_seconds()

    def _refresh_summary(self) -> None:
        for section in self._sections.values():
            if section.first_started_at and section.completed_at:
                section.latency_ms = (
                    section.completed_at - section.first_started_at
                ).total_seconds() * 1000.0

        summary = GenerationReportSummary()
        summary.planned_sections = max(len(self._sections), self._report.section_count or 0)
        summary.ready_sections = sum(
            1 for section in self._sections.values() if section.status == "ready"
        )
        summary.missing_sections = max(summary.planned_sections - summary.ready_sections, 0)
        summary.failed_sections = sum(
            1 for section in self._sections.values() if section.status == "failed"
        )
        summary.stalled_sections = sum(
            1 for section in self._sections.values() if section.status == "stalled"
        )
        summary.retry_count = sum(len(section.queued_retries) for section in self._sections.values())
        summary.validation_repair_attempts = sum(
            section.validation_repair_attempts for section in self._sections.values()
        )
        summary.validation_repair_successes = sum(
            section.validation_repair_successes for section in self._sections.values()
        )
        summary.qc_rerenders = summary.retry_count
        summary.warning_count = sum(len(section.warnings) for section in self._sections.values())
        summary.blocking_issue_count = sum(
            1
            for section in self._sections.values()
            for issue in section.issues
            if issue.severity == "blocking"
        )

        llm_calls = [
            llm_call
            for node in list(self._generation_nodes.values()) + list(self._section_nodes.values())
            for llm_call in node.llm_calls
        ]
        summary.llm_transport_retries = sum(
            1 for call in llm_calls if call.status == "failed" and call.retryable
        )
        summary.total_llm_calls = len(llm_calls)
        summary.total_tokens_in = sum(call.tokens_in or 0 for call in llm_calls)
        summary.total_tokens_out = sum(call.tokens_out or 0 for call in llm_calls)
        known_costs = [call.cost_usd for call in llm_calls if call.cost_usd is not None]
        summary.total_cost_usd = sum(known_costs) if known_costs else None

        diagram_nodes_by_section: dict[str, list[GenerationReportNode]] = {}
        for (section_id, node_name, _attempt), node in self._section_nodes.items():
            if node_name != "diagram_generator":
                continue
            diagram_nodes_by_section.setdefault(section_id, []).append(node)
        summary.diagram_retries = sum(
            max(len(nodes) - 1, 0) for nodes in diagram_nodes_by_section.values()
        )
        summary.diagram_timeout_count = sum(
            1
            for nodes in diagram_nodes_by_section.values()
            for node in nodes
            if node.error and "timed out" in node.error.lower()
        )
        summary.diagram_skip_count = sum(
            1
            for section in self._sections.values()
            if section.diagram_outcome == "skipped"
        )

        all_nodes = list(self._generation_nodes.values()) + list(self._section_nodes.values())
        slowest_node = max(
            (node for node in all_nodes if node.latency_ms is not None),
            key=lambda item: item.latency_ms or 0.0,
            default=None,
        )
        if slowest_node is not None:
            label = slowest_node.node
            summary.slowest_node = label
            summary.slowest_node_latency_ms = slowest_node.latency_ms

        slowest_section = max(
            (section for section in self._sections.values() if section.latency_ms is not None),
            key=lambda item: item.latency_ms or 0.0,
            default=None,
        )
        if slowest_section is not None:
            summary.slowest_section = slowest_section.section_id
            summary.slowest_section_latency_ms = slowest_section.latency_ms

        self._report.summary = summary

    def _sync_views(self) -> None:
        self._report.sections = sorted(
            self._sections.values(),
            key=lambda item: (item.position if item.position is not None else 9999, item.section_id),
        )
        self._report.generation_nodes = sorted(
            self._generation_nodes.values(),
            key=lambda item: (item.node, item.attempt or 0),
        )
        for section in self._report.sections:
            section.nodes = sorted(
                (
                    node
                    for (section_id, _name, _attempt), node in self._section_nodes.items()
                    if section_id == section.section_id
                ),
                key=lambda item: (item.node, item.attempt or 0),
            )

    async def _persist(self) -> None:
        self._sync_views()
        await self._repository.save_report(self._report)

    def _drain_queue(self, *, mark_dead: bool = True) -> None:
        if self._queue is None:
            return
        drained = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained:
            self._dropped_event_count += drained
            if mark_dead:
                self._consumer_dead = True
            logger.warning(
                "Recorder dropped %s queued events for generation=%s",
                drained,
                self._generation.id,
            )

    def _log_event(self, payload: dict[str, Any]) -> None:
        if payload.get("type") == "llm_call_started":
            logger.info(
                "LLM trace generation=%s event=started node=%s section=%s attempt=%s family=%s model=%s endpoint=%s",
                self._report.generation_id,
                self._caller(payload) or payload.get("node"),
                payload.get("section_id", "-"),
                payload.get("attempt"),
                payload.get("family", "-"),
                payload.get("model_name", "-"),
                payload.get("endpoint_host", "-"),
            )
        elif payload.get("type") == "llm_call_succeeded":
            logger.info(
                "LLM trace generation=%s event=succeeded node=%s section=%s attempt=%s latency_ms=%s tokens_in=%s tokens_out=%s cost_usd=%s family=%s model=%s endpoint=%s",
                self._report.generation_id,
                self._caller(payload) or payload.get("node"),
                payload.get("section_id", "-"),
                payload.get("attempt"),
                payload.get("latency_ms", "-"),
                payload.get("tokens_in", "-"),
                payload.get("tokens_out", "-"),
                payload.get("cost_usd", "-"),
                payload.get("family", "-"),
                payload.get("model_name", "-"),
                payload.get("endpoint_host", "-"),
            )
        elif payload.get("type") == "llm_call_failed":
            logger.warning(
                "Generation report generation=%s llm_failure node=%s section=%s attempt=%s retryable=%s error=%s",
                self._report.generation_id,
                self._caller(payload) or payload.get("node"),
                payload.get("section_id", "-"),
                payload.get("attempt"),
                payload.get("retryable"),
                payload.get("error"),
            )
        elif payload.get("type") == "node_finished" and payload.get("status") == "failed":
            logger.warning(
                "Generation report generation=%s node_failure node=%s section=%s attempt=%s error=%s",
                self._report.generation_id,
                self._caller(payload) or payload.get("node"),
                payload.get("section_id", "-"),
                payload.get("attempt"),
                payload.get("error"),
            )
        elif payload.get("type") == "section_retry_queued":
            logger.warning(
                "Generation report generation=%s retry_queued section=%s next_attempt=%s reason=%s",
                self._report.generation_id,
                payload.get("section_id"),
                payload.get("next_attempt"),
                payload.get("reason"),
            )
        elif payload.get("type") == "section_failed":
            logger.warning(
                "Generation report generation=%s section_failed section=%s node=%s error_type=%s error=%s",
                self._report.generation_id,
                payload.get("section_id"),
                payload.get("failed_at_node"),
                payload.get("error_type"),
                payload.get("error_summary"),
            )

    def _log_final_summary(self) -> None:
        logger.info(
            "Generation report summary generation=%s status=%s outcome=%s planned=%s ready=%s missing=%s failed=%s stalled=%s retries=%s llm_transport_retries=%s validation_repairs=%s validation_repair_successes=%s diagram_retries=%s diagram_timeouts=%s diagram_skips=%s warnings=%s blocking_issues=%s tokens_in=%s tokens_out=%s cost_usd=%s slowest_node=%s slowest_section=%s",
            self._report.generation_id,
            self._report.status,
            self._report.outcome or "-",
            self._report.summary.planned_sections,
            self._report.summary.ready_sections,
            self._report.summary.missing_sections,
            self._report.summary.failed_sections,
            self._report.summary.stalled_sections,
            self._report.summary.retry_count,
            self._report.summary.llm_transport_retries,
            self._report.summary.validation_repair_attempts,
            self._report.summary.validation_repair_successes,
            self._report.summary.diagram_retries,
            self._report.summary.diagram_timeout_count,
            self._report.summary.diagram_skip_count,
            self._report.summary.warning_count,
            self._report.summary.blocking_issue_count,
            self._report.summary.total_tokens_in,
            self._report.summary.total_tokens_out,
            (
                f"{self._report.summary.total_cost_usd:.6f}"
                if self._report.summary.total_cost_usd is not None
                else "-"
            ),
            self._report.summary.slowest_node or "-",
            self._report.summary.slowest_section or "-",
        )

