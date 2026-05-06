from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database.models import GenerationModel


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_export_allowed(booklet_status: str) -> bool:
    return booklet_status in {
        "final_ready",
        "final_with_warnings",
        "draft_ready",
        "draft_with_warnings",
        "draft_needs_review",
    }


class V3GenerationWriter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_started(
        self,
        *,
        generation_id: str,
        user_id: str,
        subject: str,
        context: str,
        template_id: str,
        section_count: int,
    ) -> None:
        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            report_json = self._default_report(section_count=section_count)
            if model is None:
                model = GenerationModel(
                    id=generation_id,
                    user_id=user_id,
                    subject=subject,
                    context=context,
                    mode="balanced",
                    status="running",
                    requested_template_id=template_id,
                    resolved_template_id=template_id,
                    requested_preset_id="v3-studio",
                    resolved_preset_id="v3-studio",
                    section_count=section_count,
                    quality_passed=None,
                    report_json=report_json,
                )
                session.add(model)
            else:
                model.user_id = user_id
                model.subject = subject
                model.context = context
                model.mode = "balanced"
                model.status = "running"
                model.requested_template_id = template_id
                model.resolved_template_id = template_id
                model.requested_preset_id = "v3-studio"
                model.resolved_preset_id = "v3-studio"
                model.section_count = section_count
                model.quality_passed = None
                model.error = None
                model.error_type = None
                model.error_code = None
                model.completed_at = None
                model.report_json = self._merge_report(model.report_json, report_json)
            await session.commit()

    async def write_draft(self, generation_id: str, payload: dict[str, Any]) -> None:
        await self._write_pack_event(
            generation_id=generation_id,
            payload=payload,
            process_status="running",
        )

    async def write_final(self, generation_id: str, payload: dict[str, Any]) -> None:
        await self._write_pack_event(
            generation_id=generation_id,
            payload=payload,
            process_status="running",
        )

    async def write_generation_complete(self, generation_id: str, payload: dict[str, Any]) -> None:
        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            if model is None:
                return
            report = self._coerce_report(model.report_json, section_count=model.section_count or 0)
            coherence = payload.get("coherence_review")
            if isinstance(coherence, dict):
                report["coherence"] = {
                    "status": coherence.get("status"),
                    "issues": coherence.get("issues", []),
                    "repair_targets": coherence.get("repair_targets", []),
                    "repaired_target_ids": coherence.get("repaired_target_ids", []),
                }
                summary = report.get("summary", {})
                if isinstance(summary, dict):
                    summary["blocking_issues"] = int(coherence.get("blocking_count") or 0)
                    summary["major_issues"] = int(coherence.get("major_count") or 0)
                    summary["minor_issues"] = int(coherence.get("minor_count") or 0)
                    report["summary"] = summary
            model.report_json = report
            await session.commit()

    async def write_resource_finalised(self, generation_id: str, payload: dict[str, Any]) -> None:
        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            if model is None:
                return
            status = str(payload.get("status") or "")
            booklet_status = str(payload.get("booklet_status") or "")
            report = self._coerce_report(model.report_json, section_count=model.section_count or 0)
            report["booklet_status"] = booklet_status or report.get("booklet_status", "streaming_preview")

            if status in {"passed", "passed_with_warnings"}:
                model.status = "completed"
                model.quality_passed = True
                report["process_status"] = "completed"
            elif model.document_json:
                model.status = "partial"
                model.quality_passed = False
                report["process_status"] = "failed_finalisation"
            else:
                model.status = "failed"
                model.quality_passed = False
                report["process_status"] = "failed"

            summary = report.get("summary")
            if isinstance(summary, dict):
                summary["export_allowed"] = _is_export_allowed(str(report.get("booklet_status") or ""))
                report["summary"] = summary

            model.completed_at = _utc_now_naive()
            model.report_json = report
            await session.commit()

    async def write_failure(
        self,
        generation_id: str,
        *,
        message: str,
        error_type: str = "generation_warning",
        error_code: str = "v3_generation_warning",
    ) -> None:
        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            if model is None:
                return
            model.status = "failed"
            model.quality_passed = False
            model.error = message
            model.error_type = error_type
            model.error_code = error_code
            model.completed_at = _utc_now_naive()
            report = self._coerce_report(model.report_json, section_count=model.section_count or 0)
            report["process_status"] = "failed"
            model.report_json = report
            await session.commit()

    async def write_pdf_status(
        self,
        generation_id: str,
        *,
        status: str,
        error: str | None,
    ) -> None:
        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            if model is None:
                return
            report = self._coerce_report(model.report_json, section_count=model.section_count or 0)
            pdf = report.get("pdf", {})
            if not isinstance(pdf, dict):
                pdf = {}
            pdf["last_export_status"] = status
            pdf["last_error"] = error
            report["pdf"] = pdf
            model.report_json = report
            await session.commit()

    async def _write_pack_event(
        self,
        *,
        generation_id: str,
        payload: dict[str, Any],
        process_status: str,
    ) -> None:
        pack = payload.get("pack")
        if not isinstance(pack, dict):
            return

        async with self._session_factory() as session:
            model = await session.get(GenerationModel, generation_id)
            if model is None:
                return
            booklet_status = str(payload.get("booklet_status") or pack.get("status") or "streaming_preview")
            planned_sections = model.section_count or 0
            assembled_sections = len(pack.get("sections", [])) if isinstance(pack.get("sections"), list) else 0

            model.document_json = {"kind": "v3_booklet_pack", **pack}
            report = self._coerce_report(model.report_json, section_count=planned_sections)
            report["process_status"] = process_status
            report["booklet_status"] = booklet_status
            summary = report.get("summary", {})
            if not isinstance(summary, dict):
                summary = {}
            summary["planned_sections"] = planned_sections
            summary["assembled_sections"] = assembled_sections
            summary["failed_sections"] = max(planned_sections - assembled_sections, 0)
            summary["export_allowed"] = _is_export_allowed(booklet_status)
            report["summary"] = summary
            model.report_json = report
            await session.commit()

    def _default_report(self, *, section_count: int) -> dict[str, Any]:
        return {
            "process_status": "running",
            "booklet_status": "streaming_preview",
            "summary": {
                "planned_sections": section_count,
                "assembled_sections": 0,
                "failed_sections": 0,
                "planned_visuals": 0,
                "delivered_visuals": 0,
                "planned_questions": 0,
                "delivered_questions": 0,
                "blocking_issues": 0,
                "major_issues": 0,
                "minor_issues": 0,
                "export_allowed": False,
            },
            "sections": [],
            "coherence": {
                "status": "pending",
                "issues": [],
                "repair_targets": [],
                "repaired_target_ids": [],
            },
            "pdf": {
                "last_export_status": "not_attempted",
                "last_error": None,
            },
        }

    def _merge_report(self, current: Any, baseline: dict[str, Any]) -> dict[str, Any]:
        report = self._coerce_report(current, section_count=baseline["summary"]["planned_sections"])
        if not isinstance(report.get("pdf"), dict):
            report["pdf"] = baseline["pdf"]
        if not isinstance(report.get("coherence"), dict):
            report["coherence"] = baseline["coherence"]
        if not isinstance(report.get("summary"), dict):
            report["summary"] = baseline["summary"]
        return report

    def _coerce_report(self, current: Any, *, section_count: int) -> dict[str, Any]:
        if isinstance(current, dict):
            report = deepcopy(current)
        else:
            report = self._default_report(section_count=section_count)
        report.setdefault("process_status", "running")
        report.setdefault("booklet_status", "streaming_preview")
        report.setdefault("sections", [])
        report.setdefault(
            "coherence",
            {
                "status": "pending",
                "issues": [],
                "repair_targets": [],
                "repaired_target_ids": [],
            },
        )
        report.setdefault(
            "pdf",
            {
                "last_export_status": "not_attempted",
                "last_error": None,
            },
        )
        summary = report.get("summary")
        if not isinstance(summary, dict):
            summary = {}
        summary.setdefault("planned_sections", section_count)
        summary.setdefault("assembled_sections", 0)
        summary.setdefault("failed_sections", 0)
        summary.setdefault("planned_visuals", 0)
        summary.setdefault("delivered_visuals", 0)
        summary.setdefault("planned_questions", 0)
        summary.setdefault("delivered_questions", 0)
        summary.setdefault("blocking_issues", 0)
        summary.setdefault("major_issues", 0)
        summary.setdefault("minor_issues", 0)
        summary.setdefault("export_allowed", False)
        report["summary"] = summary
        return report


__all__ = ["V3GenerationWriter"]
