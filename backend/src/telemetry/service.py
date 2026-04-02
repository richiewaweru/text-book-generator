from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from core.database.models import GenerationModel
from core.database.session import async_session_factory
from core.events import event_bus
from pipeline.api import PipelineDocument
from pipeline.reporting import GenerationReport, GenerationReportSection, GenerationReportSummary
from telemetry.recorder import GenerationReportRecorder
from telemetry.repositories.sql_generation_report_repo import SqlGenerationReportRepository
from telemetry.repositories.sql_llm_call_repo import SqlLLMCallRepository

logger = logging.getLogger(__name__)

_REPORT_EVENT_TYPES = {
    "pipeline_start",
    "section_started",
    "section_attempt_started",
    "node_started",
    "node_finished",
    "llm_call_started",
    "llm_call_succeeded",
    "llm_call_failed",
    "section_report_updated",
    "section_retry_queued",
    "section_failed",
    "validation_repair_attempted",
    "validation_repair_succeeded",
    "diagram_outcome",
    "section_ready",
    "complete",
    "error",
}


@dataclass
class _TraceRegistration:
    user_id: str
    source: str


class _TraceRegistry:
    def __init__(self) -> None:
        self._items: dict[str, _TraceRegistration] = {}

    def register(self, trace_id: str, user_id: str, source: str) -> None:
        self._items[trace_id] = _TraceRegistration(user_id=user_id, source=source)

    def close(self, trace_id: str) -> None:
        self._items.pop(trace_id, None)

    def user_id_for(self, trace_id: str) -> str | None:
        registration = self._items.get(trace_id)
        return registration.user_id if registration is not None else None


class TelemetryMonitor:
    def __init__(self) -> None:
        self._queue: asyncio.Queue | None = None
        self._task: asyncio.Task | None = None
        self._registry = _TraceRegistry()
        self._default_report_repository = SqlGenerationReportRepository(
            async_session_factory,
            legacy_output_dir=None,
        )
        self._default_llm_calls = SqlLLMCallRepository(async_session_factory)
        self._report_repository_factory: Any | None = None
        self._llm_call_repository_factory: Any | None = None
        self._generation_loader: Any | None = None
        self._document_loader: Any | None = None
        self._recorders: dict[str, GenerationReportRecorder] = {}

    def configure(
        self,
        *,
        report_repository_factory=None,
        llm_call_repository_factory=None,
        generation_loader=None,
        document_loader=None,
    ) -> None:
        self._report_repository_factory = report_repository_factory
        self._llm_call_repository_factory = llm_call_repository_factory
        self._generation_loader = generation_loader
        self._document_loader = document_loader

    async def start(self) -> None:
        if self._task is not None:
            return
        self._queue = event_bus.subscribe_all()
        self._task = asyncio.create_task(self._run(), name="telemetry-monitor")

    async def stop(self) -> None:
        if self._task is None:
            return
        if self._queue is not None:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=5.0)
            except (asyncio.TimeoutError, TimeoutError):
                logger.warning("Telemetry monitor shutdown timed out while draining events")
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            if self._queue is not None:
                event_bus.unsubscribe_all(self._queue)
            self._queue = None
            self._task = None
            self._recorders.clear()

    async def backfill_failed_reports(self) -> int:
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationModel).where(
                    GenerationModel.status == "failed",
                )
            )
            models = [
                model for model in result.scalars().all() if model.report_json is None
            ]

        count = 0
        repository = await self._get_report_repository()
        for model in models:
            report = self._build_backfill_report(model)
            await repository.save_report(report)
            count += 1
        return count

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            payload = await self._queue.get()
            try:
                await self._handle_event(dict(payload))
            except Exception:
                logger.exception("Telemetry monitor failed while processing event=%s", payload)
            finally:
                self._queue.task_done()

    async def _handle_event(self, payload: dict) -> None:
        event_type = payload.get("type")
        trace_id = payload.get("trace_id") or payload.get("generation_id")
        generation_id = payload.get("generation_id")

        if event_type == "trace_registered":
            self._registry.register(
                payload["trace_id"],
                payload["user_id"],
                payload["source"],
            )
            return

        if event_type == "trace_closed":
            self._registry.close(payload["trace_id"])
            return

        if event_type in {"llm_call_succeeded", "llm_call_failed"} and trace_id:
            user_id = self._registry.user_id_for(trace_id)
            if user_id is None and generation_id:
                user_id = await self._user_id_for_generation(generation_id)
            try:
                llm_calls = await self._get_llm_call_repository()
                await llm_calls.save_call(
                    trace_id=trace_id,
                    generation_id=generation_id,
                    user_id=user_id,
                    caller=payload.get("caller") or payload.get("node") or "unknown",
                    slot=payload.get("slot", "unknown"),
                    family=payload.get("family"),
                    model_name=payload.get("model_name"),
                    endpoint_host=payload.get("endpoint_host"),
                    attempt=payload.get("attempt", 1),
                    section_id=payload.get("section_id"),
                    status="succeeded" if event_type == "llm_call_succeeded" else "failed",
                    latency_ms=payload.get("latency_ms"),
                    tokens_in=payload.get("tokens_in"),
                    tokens_out=payload.get("tokens_out"),
                    cost_usd=payload.get("cost_usd"),
                    error=payload.get("error"),
                )
            except Exception:
                logger.exception(
                    "Telemetry monitor failed to persist llm_call trace_id=%s generation_id=%s",
                    trace_id,
                    generation_id,
                )

        if event_type in _REPORT_EVENT_TYPES and generation_id:
            recorder = await self._ensure_recorder(generation_id)
            if recorder is None:
                return
            if event_type == "complete":
                await recorder.apply_event(payload)
                await recorder.finalize_success(
                    document=await self._load_document(generation_id),
                    generation_time_seconds=await self._generation_time_seconds(generation_id),
                )
                recorder.log_final_summary()
                self._recorders.pop(generation_id, None)
                self._registry.close(generation_id)
                return
            if event_type == "error":
                await recorder.apply_event(payload)
                await recorder.finalize_failure(
                    error=payload.get("message", "Generation failed"),
                    generation_time_seconds=await self._generation_time_seconds(generation_id),
                )
                recorder.log_final_summary()
                self._recorders.pop(generation_id, None)
                self._registry.close(generation_id)
                return

            await recorder.apply_event(payload)

    async def _ensure_recorder(self, generation_id: str) -> GenerationReportRecorder | None:
        existing = self._recorders.get(generation_id)
        if existing is not None:
            return existing

        generation = await self._load_generation(generation_id)
        if generation is None:
            return None

        recorder = GenerationReportRecorder(
            generation=self._report_generation_descriptor(generation),
            repository=await self._get_report_repository(),
        )
        self._recorders[generation_id] = recorder
        return recorder

    async def _user_id_for_generation(self, generation_id: str) -> str | None:
        generation = await self._load_generation(generation_id)
        if generation is not None:
            return getattr(generation, "user_id", None)
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationModel.user_id).where(GenerationModel.id == generation_id)
            )
            row = result.first()
            return row[0] if row is not None else None

    async def _generation_time_seconds(self, generation_id: str) -> float | None:
        generation = await self._load_generation(generation_id)
        if generation is not None:
            return getattr(generation, "generation_time_seconds", None)
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationModel.generation_time_seconds).where(
                    GenerationModel.id == generation_id
                )
            )
            row = result.first()
            return row[0] if row is not None else None

    async def _load_document(self, generation_id: str) -> PipelineDocument:
        generation = await self._load_generation(generation_id)
        if generation is not None and self._document_loader is not None:
            document_ref = getattr(generation, "document_path", None) or generation_id
            return await self._document_loader(document_ref)
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationModel.document_json).where(GenerationModel.id == generation_id)
            )
            row = result.first()
        if row is None or not row[0]:
            raise FileNotFoundError(generation_id)
        payload = row[0]
        if isinstance(payload, str):
            return PipelineDocument.model_validate_json(payload)
        return PipelineDocument.model_validate(payload)

    async def _get_report_repository(self):
        if self._report_repository_factory is not None:
            repository = await self._report_repository_factory()
            if repository is not None:
                return repository
        return self._default_report_repository

    async def _get_llm_call_repository(self):
        if self._llm_call_repository_factory is not None:
            repository = await self._llm_call_repository_factory()
            if repository is not None:
                return repository
        return self._default_llm_calls

    async def _load_generation(self, generation_id: str):
        if self._generation_loader is not None:
            generation = await self._generation_loader(generation_id)
            if generation is not None:
                return generation
        async with async_session_factory() as session:
            result = await session.execute(
                select(GenerationModel).where(GenerationModel.id == generation_id)
            )
            return result.scalar_one_or_none()

    def _report_generation_descriptor(self, generation) -> SimpleNamespace:
        requested_template_id = getattr(generation, "requested_template_id", None)
        resolved_template_id = getattr(generation, "resolved_template_id", None)
        requested_preset_id = getattr(generation, "requested_preset_id", None)
        resolved_preset_id = getattr(generation, "resolved_preset_id", None)
        return SimpleNamespace(
            id=generation.id,
            subject=generation.subject,
            context=generation.context,
            requested_template_id=resolved_template_id or requested_template_id,
            requested_preset_id=resolved_preset_id or requested_preset_id,
            section_count=generation.section_count,
            created_at=generation.created_at,
        )

    def _build_backfill_report(self, model: GenerationModel) -> GenerationReport:
        report = GenerationReport(
            generation_id=model.id,
            subject=model.subject,
            context=model.context,
            template_id=model.resolved_template_id or model.requested_template_id,
            preset_id=model.resolved_preset_id or model.requested_preset_id,
            status="failed",
            outcome="failed",
            section_count=model.section_count,
            quality_passed=False,
            started_at=model.created_at,
            completed_at=model.completed_at or datetime.now(timezone.utc),
            generation_time_seconds=model.generation_time_seconds,
            final_error=model.error,
            summary=GenerationReportSummary(),
        )
        if model.document_json:
            payload = model.document_json
            document = (
                PipelineDocument.model_validate_json(payload)
                if isinstance(payload, str)
                else PipelineDocument.model_validate(payload)
            )
            report.section_count = len(document.section_manifest) or report.section_count
            for item in document.section_manifest:
                section_id = item["section_id"] if isinstance(item, dict) else item.section_id
                title = item.get("title") if isinstance(item, dict) else item.title
                position = item.get("position") if isinstance(item, dict) else item.position
                status = "ready" if any(
                    section.section_id == section_id for section in document.sections
                ) else "failed"
                report.sections.append(
                    GenerationReportSection(
                        section_id=section_id,
                        title=title,
                        position=position,
                        status=status,
                    )
                )
            report.summary.ready_sections = sum(
                1 for section in report.sections if section.status == "ready"
            )
            report.summary.failed_sections = sum(
                1 for section in report.sections if section.status == "failed"
            )
            report.summary.planned_sections = len(report.sections)
            report.summary.missing_sections = max(
                report.summary.planned_sections - report.summary.ready_sections,
                0,
            )
        return report


telemetry_monitor = TelemetryMonitor()
