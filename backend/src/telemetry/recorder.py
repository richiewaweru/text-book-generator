from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from pipeline.api import PipelineDocument, PipelineSectionReport
from pipeline.contracts import get_section_field_for_component
import core.events as core_events
from pipeline.media.retry import is_media_block
from pipeline.reporting import (
    GenerationPlannerTrace,
    GenerationPlannerTraceSection,
    GenerationReport,
    GenerationReportFieldRegenAttempt,
    GenerationReportLLMAttempt,
    GenerationReportNode,
    GenerationReportOutlineSection,
    GenerationReportRetry,
    GenerationReportSection,
    GenerationReportSummary,
    GenerationTimelineEvent,
    MediaDecisionTrace,
)
from telemetry.ports.generation_report_repository import GenerationReportRepository

logger = logging.getLogger(__name__)

_TIMELINE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "pipeline_start",
        "curriculum_planned",
        "section_started",
        "section_attempt_started",
        "llm_call_started",
        "llm_call_succeeded",
        "llm_call_failed",
        "field_regen_outcome",
        "section_retry_queued",
        "section_failed",
        "section_final",
        "complete",
        "generation_started",
        "generation_complete",
        "resource_finalised",
        "generation_warning",
        "coherence_report_ready",
    }
)

_TIMELINE_CONDITIONAL_TYPES: frozenset[str] = frozenset(
    {
        "image_outcome",
        "diagram_outcome",
        "media_plan_ready",
        "interaction_outcome",
    }
)

_SECTION_META_FIELDS: frozenset[str] = frozenset({"section_id", "template_id"})


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
        self._repository = repository
        self._generation = generation
        self._plan_components: dict[str, list[str]] = {}
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
            pipeline_version=getattr(generation, "pipeline_version", "v2"),
        )
        self._sections: dict[str, GenerationReportSection] = {}
        self._generation_nodes: dict[tuple[str, int | None], GenerationReportNode] = {}
        self._section_nodes: dict[tuple[str, str, int | None], GenerationReportNode] = {}
        self._planned_media_slots: dict[str, set[str]] = {}
        self._ready_media_slots: dict[str, set[str]] = {}
        self._failed_media_slots: dict[str, set[str]] = {}
        self._image_slot_ids: set[tuple[str, str]] = set()
        self._svg_slot_ids: set[tuple[str, str]] = set()
        self._prompt_builder_slot_ids: set[tuple[str, str]] = set()
        self._sections_without_media_ids: set[str] = set()
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

    async def finalize_runtime_success(
        self,
        *,
        quality_passed: bool | None = None,
        generation_time_seconds: float | None = None,
    ) -> None:
        self._report.status = "completed"
        self._report.quality_passed = quality_passed
        self._report.generation_time_seconds = generation_time_seconds
        self._report.completed_at = self._report.completed_at or _utc_now()
        self._finalize_incomplete_sections(final_status="completed")
        self._report.outcome = self._derive_outcome(final_status="completed")
        self._update_wall_time()
        self._refresh_summary()
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
        elif event_type == "curriculum_planned":
            self._handle_curriculum_planned(payload)
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
        elif event_type == "media_plan_ready":
            self._handle_media_plan_ready(payload)
        elif event_type == "visual_placements_committed":
            self._handle_visual_placements_committed(payload)
        elif event_type == "slot_render_mode_resolved":
            self._handle_slot_render_mode_resolved(payload)
        elif event_type == "simulation_type_selected":
            self._handle_simulation_type_selected(payload)
        elif event_type == "intent_resolved":
            self._handle_intent_resolved(payload)
        elif event_type == "media_slot_ready":
            self._handle_media_slot_ready(payload)
        elif event_type == "media_slot_failed":
            self._handle_media_slot_failed(payload)
        elif event_type == "section_media_blocked":
            self._handle_section_media_blocked(payload)
        elif event_type == "section_failed":
            self._handle_section_failed(payload)
        elif event_type == "validation_repair_attempted":
            self._handle_validation_repair_attempted(payload)
        elif event_type == "validation_repair_succeeded":
            self._handle_validation_repair_succeeded(payload)
        elif event_type == "diagram_outcome":
            self._handle_diagram_outcome(payload)
        elif event_type == "image_outcome":
            self._handle_image_outcome(payload)
        elif event_type == "interaction_outcome":
            self._handle_interaction_outcome(payload)
        elif event_type == "interaction_retry_queued":
            self._handle_interaction_retry_queued(payload)
        elif event_type == "field_regen_outcome":
            self._handle_field_regen_outcome(payload)
        elif event_type == "section_ready":
            self._handle_section_ready(payload)
        elif event_type == "complete":
            self._handle_complete(payload)
        elif event_type == "error":
            self._handle_error(payload)
        elif event_type == "generation_started":
            self._handle_pipeline_start(payload)
        elif event_type == "section_writing_started":
            self._handle_section_started(payload)
        elif event_type == "questions_started":
            self._handle_section_started(payload)
        elif event_type == "component_ready":
            self._handle_component_ready(payload)
        elif event_type == "question_ready":
            self._handle_section_started(payload)
        elif event_type == "generation_complete":
            self._handle_generation_complete(payload)
        elif event_type == "generation_warning":
            self._handle_generation_warning(payload)
        elif event_type == "resource_finalised":
            self._handle_resource_finalised(payload)
        elif event_type == "coherence_report_ready":
            self._handle_coherence_report_ready(payload)

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
        event_type = payload.get("type", "unknown")
        if not self._should_include_in_timeline(event_type, payload):
            return
        self._timeline_sequence += 1
        self._report.timeline.append(
            GenerationTimelineEvent(
                sequence=self._timeline_sequence,
                type=event_type,
                timestamp=self._event_timestamp(payload),
                node=self._caller(payload) or payload.get("node"),
                section_id=payload.get("section_id"),
                attempt=payload.get("attempt"),
                payload=payload,
            )
        )

    def _should_include_in_timeline(self, event_type: str, payload: dict[str, Any]) -> bool:
        if event_type in _TIMELINE_EVENT_TYPES:
            return True
        if event_type not in _TIMELINE_CONDITIONAL_TYPES:
            return False
        if event_type in {"image_outcome", "diagram_outcome"}:
            return payload.get("outcome") != "skipped"
        if event_type == "media_plan_ready":
            return int(payload.get("slot_count", 0) or 0) > 0
        if event_type == "interaction_outcome":
            return payload.get("outcome") == "generated"
        return False

    def _resolve_planned_fields(self, section_id: str) -> list[str]:
        planned_ids = self._plan_components.get(section_id, [])
        resolved = []
        for component_id in planned_ids:
            field_name = get_section_field_for_component(component_id)
            if field_name:
                resolved.append(field_name)
        return sorted(set(resolved))

    def _refresh_section_expectations(self, section: GenerationReportSection) -> None:
        section.expected_components = self._resolve_planned_fields(section.section_id)
        if section.delivered_components:
            delivered = set(section.delivered_components)
            section.missing_components = [
                component for component in section.expected_components if component not in delivered
            ]
        else:
            section.missing_components = list(section.expected_components)

    def _ensure_section(self, section_id: str) -> GenerationReportSection:
        if section_id not in self._sections:
            self._sections[section_id] = GenerationReportSection(
                section_id=section_id,
            )
            self._refresh_section_expectations(self._sections[section_id])
        return self._sections[section_id]

    def _slot_set(self, store: dict[str, set[str]], section_id: str) -> set[str]:
        return store.setdefault(section_id, set())

    def _executor_for_media_slot(self, slot_type: str | None, render: str | None) -> str | None:
        if slot_type == "simulation":
            return "interaction_generator"
        if slot_type in {"diagram", "diagram_compare", "diagram_series"}:
            if render == "svg":
                return "diagram_generator"
            if render == "image":
                return "image_generator"
        return None

    def _decision_for_slot(
        self,
        section: GenerationReportSection,
        slot_id: str,
    ) -> MediaDecisionTrace | None:
        return next(
            (decision for decision in section.media_decisions if decision.slot_id == slot_id),
            None,
        )

    def _upsert_media_decision(
        self,
        section: GenerationReportSection,
        decision: MediaDecisionTrace,
    ) -> None:
        for index, existing in enumerate(section.media_decisions):
            if existing.slot_id == decision.slot_id:
                section.media_decisions[index] = existing.model_copy(
                    update=decision.model_dump(exclude_none=True)
                )
                return
        section.media_decisions.append(decision)

    def _set_media_decision_status(
        self,
        section: GenerationReportSection,
        *,
        executor: str,
        status: str,
    ) -> None:
        for index, decision in enumerate(section.media_decisions):
            if decision.executor_selected == executor:
                section.media_decisions[index] = decision.model_copy(update={"status": status})

    def _svg_metadata_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        update: dict[str, Any] = {}
        for key in (
            "svg_generation_mode",
            "model_slot",
            "diagram_kind",
            "sanitized",
            "intent_validated",
            "svg_failure_reason",
        ):
            if key in payload:
                update[key] = payload.get(key)
        return update

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

    def _handle_curriculum_planned(self, payload: dict[str, Any]) -> None:
        planner_sections = [
            GenerationPlannerTraceSection.model_validate(item)
            for item in payload.get("planner_trace_sections", [])
        ]
        planner_counts = {
            section.section_id: section.visual_placements_count for section in planner_sections
        }
        outline = []
        for item in payload.get("runtime_curriculum_outline", []):
            normalized = dict(item)
            normalized["visual_placements_count"] = normalized.get(
                "visual_placements_count",
                planner_counts.get(normalized.get("section_id", ""), 0),
            )
            outline.append(GenerationReportOutlineSection.model_validate(normalized))
        self._plan_components = {
            section.section_id: list(section.required_components)
            for section in outline
        }
        for section_id in self._sections:
            self._refresh_section_expectations(self._sections[section_id])
        self._report.runtime_curriculum_outline = outline
        self._report.planner_trace = GenerationPlannerTrace(
            path=payload["path"],
            result=payload["result"],
            duplicate_term_warnings=list(payload.get("duplicate_term_warnings", [])),
            sections=planner_sections,
        )
        if outline:
            self._report.section_count = max(
                self._report.section_count or 0,
                len(outline),
            )

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
        self._refresh_section_expectations(section)
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
        llm.thinking_tokens = payload.get("thinking_tokens")
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
            node=payload.get("node") or self._caller(payload) or "",
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
        node_name = payload.get("node") or self._caller(payload) or "unknown"
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
        if is_media_block(payload.get("block_type")):
            section.media_frame_retry_count += 1

    def _handle_media_plan_ready(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section_id = payload["section_id"]
        slot_count = payload.get("slot_count", 0)
        section.media_slots_planned = max(section.media_slots_planned, slot_count)
        slots = list(payload.get("slots", []) or [])
        if slot_count == 0 or not slots:
            if slot_count == 0:
                self._sections_without_media_ids.add(section_id)
            return
        self._sections_without_media_ids.discard(section_id)
        for slot in slots:
            slot_id = str(slot.get("slot_id") or "")
            if not slot_id:
                continue
            slot_type = str(slot.get("slot_type") or "")
            final_render = str(slot.get("preferred_render_final") or "")
            self._slot_set(self._planned_media_slots, section_id).add(slot_id)
            slot_key = (section_id, slot_id)
            if final_render == "image":
                self._image_slot_ids.add(slot_key)
                self._svg_slot_ids.discard(slot_key)
            elif final_render == "svg":
                self._svg_slot_ids.add(slot_key)
                self._image_slot_ids.discard(slot_key)
            if slot.get("decision_source") == "intelligent_image_prompt":
                self._prompt_builder_slot_ids.add(slot_key)
            self._upsert_media_decision(
                section,
                MediaDecisionTrace(
                    slot_id=slot_id,
                    slot_type=slot_type,
                    preferred_render_initial=str(
                        slot.get("preferred_render_initial") or final_render
                    ),
                    preferred_render_final=final_render,
                    fallback_render=slot.get("fallback_render"),
                    decision_source=str(slot.get("decision_source") or "slot_type_default"),
                    decision_reason=slot.get("decision_reason"),
                    intelligent_prompt_resolved=bool(
                        slot.get("intelligent_prompt_resolved", False)
                    ),
                    executor_selected=self._executor_for_media_slot(slot_type, final_render),
                    status="planned",
                ),
            )
        section.media_slots_planned = max(
            section.media_slots_planned,
            len(self._planned_media_slots.get(section_id, set())),
        )

    def _handle_visual_placements_committed(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.visual_placements_count = payload.get("placements_count", 0)
        section.visual_placements_summary = list(payload.get("placements_summary", []))

    def _handle_slot_render_mode_resolved(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        slot_id = payload.get("slot_id")
        if not section_id or not slot_id:
            return
        section = self._ensure_section(section_id)
        render_mode = payload.get("render_mode", "")
        section.slot_render_modes[slot_id] = render_mode
        slot_key = (section_id, slot_id)
        if render_mode == "image":
            self._image_slot_ids.add(slot_key)
            self._svg_slot_ids.discard(slot_key)
        else:
            self._svg_slot_ids.add(slot_key)
            self._image_slot_ids.discard(slot_key)
        if payload.get("decided_by") == "intelligent_image_prompt":
            self._prompt_builder_slot_ids.add(slot_key)
        existing = self._decision_for_slot(section, slot_id)
        if existing is not None:
            self._upsert_media_decision(
                section,
                existing.model_copy(
                    update={
                        "preferred_render_initial": payload.get(
                            "preferred_render_initial",
                            existing.preferred_render_initial,
                        ),
                        "preferred_render_final": payload.get(
                            "preferred_render_final",
                            render_mode,
                        ),
                        "fallback_render": payload.get(
                            "fallback_render",
                            existing.fallback_render,
                        ),
                        "decision_source": payload.get("decided_by")
                        or existing.decision_source,
                        "decision_reason": payload.get(
                            "decision_reason",
                            existing.decision_reason,
                        ),
                        "intelligent_prompt_resolved": bool(
                            payload.get(
                                "intelligent_prompt_resolved",
                                existing.intelligent_prompt_resolved,
                            )
                        ),
                        "executor_selected": self._executor_for_media_slot(
                            existing.slot_type,
                            payload.get("preferred_render_final") or render_mode,
                        ),
                    }
                ),
            )

    def _handle_simulation_type_selected(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.simulation_type_selected = payload.get("simulation_type")
        section.simulation_goal_selected = payload.get("simulation_goal")

    def _handle_intent_resolved(self, payload: dict[str, Any]) -> None:
        _ = payload

    def _handle_media_slot_ready(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        slot_id = payload.get("slot_id")
        if not section_id or not slot_id:
            return
        section = self._ensure_section(section_id)
        self._slot_set(self._ready_media_slots, section_id).add(slot_id)
        self._slot_set(self._planned_media_slots, section_id).add(slot_id)
        section.media_slots_ready = len(self._ready_media_slots[section_id])
        section.media_slots_planned = max(
            section.media_slots_planned,
            len(self._planned_media_slots[section_id]),
        )
        decision = self._decision_for_slot(section, slot_id)
        if decision is not None:
            update = {"status": "generated"}
            update.update(self._svg_metadata_update(payload))
            self._upsert_media_decision(
                section,
                decision.model_copy(update=update),
            )

    def _handle_media_slot_failed(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        slot_id = payload.get("slot_id")
        if not section_id or not slot_id:
            return
        section = self._ensure_section(section_id)
        self._slot_set(self._failed_media_slots, section_id).add(slot_id)
        self._slot_set(self._planned_media_slots, section_id).add(slot_id)
        section.media_slots_failed = len(self._failed_media_slots[section_id])
        section.media_slots_planned = max(
            section.media_slots_planned,
            len(self._planned_media_slots[section_id]),
        )
        decision = self._decision_for_slot(section, slot_id)
        if decision is not None:
            update = {"status": "failed"}
            update.update(self._svg_metadata_update(payload))
            self._upsert_media_decision(
                section,
                decision.model_copy(update=update),
            )
        if payload.get("slot_type") in {"simulation", "simulation_block"}:
            section.simulation_outcome = "failed"
            section.simulation_failure_reason = payload.get("error")

    def _handle_section_media_blocked(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.media_blocked = True
        section.media_block_reason = payload.get("reason")

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
        outcome = payload.get("outcome")
        if outcome == "success":
            self._set_media_decision_status(
                section,
                executor="diagram_generator",
                status="generated",
            )
        elif outcome in {"timeout", "error"}:
            self._set_media_decision_status(
                section,
                executor="diagram_generator",
                status="failed",
            )

    def _handle_image_outcome(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        if not section_id:
            return
        section = self._ensure_section(section_id)
        section.image_outcome = payload.get("outcome")
        section.image_error = payload.get("error_message")
        section.image_provider = payload.get("provider")
        outcome = payload.get("outcome")
        if outcome == "success":
            self._set_media_decision_status(
                section,
                executor="image_generator",
                status="generated",
            )
        elif outcome in {"timeout", "error"}:
            self._set_media_decision_status(
                section,
                executor="image_generator",
                status="failed",
            )

    def _handle_interaction_outcome(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        if not section_id:
            return
        section = self._ensure_section(section_id)
        section.interaction_outcome = payload.get("outcome")
        section.interaction_skip_reason = payload.get("skip_reason")
        section.interaction_count = payload.get("interaction_count", 0)
        section.simulation_outcome = (
            "generated" if payload.get("outcome") == "generated" else "skipped"
        )
        section.simulation_failure_reason = None
        if payload.get("outcome") == "generated":
            self._set_media_decision_status(
                section,
                executor="interaction_generator",
                status="generated",
            )
        elif payload.get("outcome") == "skipped":
            self._set_media_decision_status(
                section,
                executor="interaction_generator",
                status="skipped",
            )

    def _handle_interaction_retry_queued(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        if not section_id:
            return
        section = self._ensure_section(section_id)
        section.interaction_retry_count += 1

    def _handle_field_regen_outcome(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        if not section_id:
            return
        section = self._ensure_section(section_id)
        section.field_regen_attempts.append(
            GenerationReportFieldRegenAttempt(
                field=payload.get("field_name", "unknown"),
                outcome=payload.get("outcome", "failed"),
                error=payload.get("error_message"),
            )
        )

    def _handle_section_ready(self, payload: dict[str, Any]) -> None:
        section = self._ensure_section(payload["section_id"])
        section.status = "ready"
        section.completed_at = _utc_now()
        section.final_error = None
        section.failure_detail = None
        section.media_blocked = False
        section.media_block_reason = None
        delivered = self._delivered_components(payload.get("section", {}))
        section.delivered_components = delivered
        self._refresh_section_expectations(section)

    def _handle_section_final(self, payload: dict[str, Any]) -> None:
        # section_final marks the section entering final assembly.
        # It no longer carries SectionContent (removed to reduce SSE payload).
        # Timestamps and error state are updated here; status and
        # delivered_components are resolved by the section_ready event that
        # fires immediately after this one.
        section = self._ensure_section(payload["section_id"])
        section.completed_at = _utc_now()
        section.final_error = None
        section.failure_detail = None
        section.media_blocked = False
        section.media_block_reason = None

    def _handle_complete(self, payload: dict[str, Any]) -> None:
        self._report.status = "completed"
        self._report.completed_at = _as_utc(payload.get("completed_at")) or self._report.completed_at
        self._update_wall_time()

    def _handle_error(self, payload: dict[str, Any]) -> None:
        self._report.status = "failed"
        self._report.completed_at = _as_utc(payload.get("completed_at")) or self._report.completed_at
        self._report.final_error = payload.get("message", self._report.final_error)
        self._update_wall_time()

    def _handle_component_ready(self, payload: dict[str, Any]) -> None:
        section_id = payload.get("section_id")
        if not section_id:
            return
        section = self._ensure_section(section_id)
        section.status = "running"
        field_name = payload.get("section_field")
        if isinstance(field_name, str) and field_name:
            delivered = set(section.delivered_components)
            delivered.add(field_name)
            section.delivered_components = sorted(delivered)
            self._refresh_section_expectations(section)

    def _handle_generation_complete(self, payload: dict[str, Any]) -> None:
        self._report.status = "completed"
        self._report.completed_at = _utc_now()
        coherence_review = payload.get("coherence_review")
        if isinstance(coherence_review, dict):
            self._report.coherence_review = coherence_review
        self._update_wall_time()

    def _handle_generation_warning(self, payload: dict[str, Any]) -> None:
        self._report.final_error = payload.get("message", self._report.final_error)

    def _handle_resource_finalised(self, payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status in {"passed", "passed_with_warnings"}:
            self._report.quality_passed = True
        elif status in {"escalated", "repair_required"}:
            self._report.quality_passed = False

    def _handle_coherence_report_ready(self, payload: dict[str, Any]) -> None:
        self._report.coherence_review = {
            "status": payload.get("status"),
            "blocking_count": payload.get("blocking_count"),
            "repair_target_count": payload.get("repair_target_count"),
        }

    def _delivered_components(self, section_payload: dict[str, Any]) -> list[str]:
        return sorted(
            field_name
            for field_name, value in section_payload.items()
            if field_name not in _SECTION_META_FIELDS and value
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
            self._refresh_section_expectations(section)
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
            self._refresh_section_expectations(section)
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
        summary.sections_with_planned_visuals = sum(
            1
            for section in self._report.runtime_curriculum_outline
            if section.visual_placements_count > 0
        )
        summary.retry_count = sum(len(section.queued_retries) for section in self._sections.values())
        summary.validation_repair_attempts = sum(
            section.validation_repair_attempts for section in self._sections.values()
        )
        summary.validation_repair_successes = sum(
            section.validation_repair_successes for section in self._sections.values()
        )
        summary.qc_rerenders = summary.retry_count
        summary.media_slots_planned = sum(
            section.media_slots_planned for section in self._sections.values()
        )
        summary.media_slots_ready = sum(
            section.media_slots_ready for section in self._sections.values()
        )
        summary.media_slots_failed = sum(
            section.media_slots_failed for section in self._sections.values()
        )
        summary.media_frame_retry_count = sum(
            section.media_frame_retry_count for section in self._sections.values()
        )
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
        all_media_decisions = [
            decision
            for section in self._sections.values()
            for decision in section.media_decisions
        ]
        summary.sections_without_media = len(self._sections_without_media_ids)
        summary.planned_image_slots = sum(
            1 for decision in all_media_decisions if decision.preferred_render_final == "image"
        )
        summary.planned_svg_slots = sum(
            1 for decision in all_media_decisions if decision.preferred_render_final == "svg"
        )
        summary.planned_simulation_slots = sum(
            1 for decision in all_media_decisions if decision.slot_type == "simulation"
        )
        summary.svg_attempted_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "diagram_generator"
            and decision.status in {"generated", "failed"}
        )
        summary.svg_success_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "diagram_generator"
            and decision.status == "generated"
        )
        summary.svg_failed_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "diagram_generator"
            and decision.status == "failed"
        )
        raw_svg_decisions = [
            decision
            for decision in all_media_decisions
            if decision.executor_selected == "diagram_generator"
            and decision.svg_generation_mode == "raw_svg"
        ]
        summary.raw_svg_generation_count = sum(
            1 for decision in raw_svg_decisions if decision.status in {"generated", "failed"}
        )
        summary.svg_sanitizer_failure_count = sum(
            1 for decision in raw_svg_decisions if decision.svg_failure_reason == "sanitizer"
        )
        summary.svg_validation_failure_count = sum(
            1 for decision in raw_svg_decisions if decision.svg_failure_reason == "validation"
        )
        summary.svg_intent_retry_count = sum(
            1 for decision in raw_svg_decisions if decision.svg_failure_reason == "intent"
        )
        model_slots = sorted(
            {
                decision.model_slot
                for decision in raw_svg_decisions
                if decision.model_slot
            }
        )
        summary.svg_generation_model_slot = ",".join(model_slots) if model_slots else None
        kind_counts: dict[str, int] = {}
        for decision in raw_svg_decisions:
            if decision.status != "generated" or not decision.diagram_kind:
                continue
            kind_counts[decision.diagram_kind] = kind_counts.get(decision.diagram_kind, 0) + 1
        summary.svg_diagram_kind_counts = kind_counts
        summary.image_attempted_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "image_generator"
            and decision.status in {"generated", "failed"}
        )
        summary.image_success_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "image_generator"
            and decision.status == "generated"
        )
        summary.image_failed_slots = sum(
            1
            for decision in all_media_decisions
            if decision.executor_selected == "image_generator"
            and decision.status == "failed"
        )
        summary.image_success_count = sum(
            1 for section in self._sections.values() if section.image_outcome == "success"
        )
        summary.image_failure_count = sum(
            1
            for section in self._sections.values()
            if section.image_outcome in {"timeout", "error"}
        )
        summary.image_slots_count = len(self._image_slot_ids)
        summary.svg_slots_count = len(self._svg_slot_ids)
        summary.prompt_builder_calls = len(self._prompt_builder_slot_ids)
        provider_counts: dict[str, int] = {}
        for section in self._sections.values():
            if section.image_provider:
                provider_counts[section.image_provider] = (
                    provider_counts.get(section.image_provider, 0) + 1
                )
        summary.image_provider_counts = provider_counts
        summary.simulation_success_count = sum(
            1 for section in self._sections.values() if section.simulation_outcome == "generated"
        )
        summary.simulation_failure_count = sum(
            1 for section in self._sections.values() if section.simulation_outcome == "failed"
        )
        summary.interaction_skip_count = sum(
            1
            for section in self._sections.values()
            if section.interaction_outcome == "skipped"
        )
        summary.interaction_retry_count = sum(
            section.interaction_retry_count for section in self._sections.values()
        )
        summary.field_regen_count = sum(
            len(section.field_regen_attempts) for section in self._sections.values()
        )
        summary.field_regen_success_count = sum(
            1
            for section in self._sections.values()
            for attempt in section.field_regen_attempts
            if attempt.outcome == "success"
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
            "Generation report summary generation=%s status=%s outcome=%s planned=%s ready=%s missing=%s failed=%s stalled=%s retries=%s llm_transport_retries=%s validation_repairs=%s validation_repair_successes=%s media_slots_planned=%s media_slots_ready=%s media_slots_failed=%s media_frame_retries=%s diagram_retries=%s diagram_timeouts=%s sections_without_media=%s warnings=%s blocking_issues=%s tokens_in=%s tokens_out=%s cost_usd=%s slowest_node=%s slowest_section=%s",
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
            self._report.summary.media_slots_planned,
            self._report.summary.media_slots_ready,
            self._report.summary.media_slots_failed,
            self._report.summary.media_frame_retry_count,
            self._report.summary.diagram_retries,
            self._report.summary.diagram_timeout_count,
            self._report.summary.sections_without_media,
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
        logger.info(
            "Generation report image_and_interaction_summary generation=%s image_success=%s image_fail=%s image_slots_planned=%s image_providers=%s simulation_success=%s simulation_fail=%s interaction_skip=%s interaction_retries=%s field_regen=%s field_regen_success=%s",
            self._report.generation_id,
            self._report.summary.image_success_count,
            self._report.summary.image_failure_count,
            self._report.summary.planned_image_slots,
            self._report.summary.image_provider_counts,
            self._report.summary.simulation_success_count,
            self._report.summary.simulation_failure_count,
            self._report.summary.interaction_skip_count,
            self._report.summary.interaction_retry_count,
            self._report.summary.field_regen_count,
            self._report.summary.field_regen_success_count,
        )
