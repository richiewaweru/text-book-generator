from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from core.config import Settings
from core.pdf_export_runtime import pdf_export_telemetry
from generation.entities.generation import Generation
from generation.pdf_export.cleanup import cleanup_files, ensure_temp_dir
from generation.pdf_export.components.answers import generate_answer_key_pdf
from generation.pdf_export.components.assembly import (
    add_metadata,
    add_page_numbers,
    merge_pdfs,
)
from generation.pdf_export.components.cover import clean_cover_title, generate_cover_pdf
from generation.pdf_export.components.toc import generate_toc_pdf
from generation.pdf_export.config import PDFExportConfig
from generation.pdf_export.rendering.playwright import render_generation_pdf
from pipeline.api import PipelineDocument

logger = logging.getLogger(__name__)


class PDFExportOptions(BaseModel):
    include_toc: bool = True
    include_answers: bool = True


class PDFExportRequest(PDFExportOptions):
    school_name: str = Field(min_length=1)
    teacher_name: str = Field(min_length=1)
    date: str | None = None


class PDFExportResult(BaseModel):
    pdf_path: Path
    filename: str
    file_size_bytes: int
    page_count: int
    generation_time_ms: int
    cleanup_paths: list[Path]


async def export_generation_pdf(
    *,
    generation: Generation,
    document: PipelineDocument,
    auth_token: str,
    request: PDFExportRequest,
    settings: Settings,
    request_id: str | None = None,
) -> PDFExportResult:
    config = PDFExportConfig(settings)
    if not config.enabled:
        raise RuntimeError("PDF export is disabled")

    export_id = uuid.uuid4().hex
    temp_dir = ensure_temp_dir(config.temp_dir)
    cleanup_paths: list[Path] = []
    started = time.perf_counter()

    cover_path = temp_dir / f"{generation.id}-{export_id}-cover.pdf"
    toc_path = temp_dir / f"{generation.id}-{export_id}-toc.pdf"
    content_path = temp_dir / f"{generation.id}-{export_id}-content.pdf"
    answers_path = temp_dir / f"{generation.id}-{export_id}-answers.pdf"
    final_path = temp_dir / f"{generation.id}-{export_id}-final.pdf"

    try:
        cover_title = clean_cover_title(document.subject or generation.subject)
        cover_started = time.perf_counter()
        _log_stage("cover_generation", "started", generation.id, request_id)
        generate_cover_pdf(
            output_path=cover_path,
            title=cover_title,
            school_name=request.school_name,
            teacher_name=request.teacher_name,
            date_label=request.date,
        )
        cleanup_paths.append(cover_path)
        _log_stage(
            "cover_generation",
            "completed",
            generation.id,
            request_id,
            duration_ms=_duration_ms(cover_started),
        )

        source_paths = [cover_path]
        skip_pages = 1

        if request.include_toc and document.section_manifest:
            toc_started = time.perf_counter()
            _log_stage("toc_generation", "started", generation.id, request_id)
            generate_toc_pdf(output_path=toc_path, manifest=document.section_manifest)
            cleanup_paths.append(toc_path)
            source_paths.append(toc_path)
            skip_pages += 1
            _log_stage(
                "toc_generation",
                "completed",
                generation.id,
                request_id,
                duration_ms=_duration_ms(toc_started),
            )

        content_started = time.perf_counter()
        _log_stage("content_rendering", "started", generation.id, request_id)
        await render_generation_pdf(
            output_path=content_path,
            generation_id=generation.id,
            auth_token=auth_token,
            config=config,
        )
        cleanup_paths.append(content_path)
        source_paths.append(content_path)
        _log_stage(
            "content_rendering",
            "completed",
            generation.id,
            request_id,
            duration_ms=_duration_ms(content_started),
        )

        if request.include_answers:
            answers_started = time.perf_counter()
            _log_stage("answer_key_generation", "started", generation.id, request_id)
            answer_pdf = generate_answer_key_pdf(
                output_path=answers_path,
                sections=document.sections,
            )
            if answer_pdf is not None:
                cleanup_paths.append(answer_pdf)
                source_paths.append(answer_pdf)
            _log_stage(
                "answer_key_generation",
                "completed",
                generation.id,
                request_id,
                duration_ms=_duration_ms(answers_started),
            )

        assembly_started = time.perf_counter()
        _log_stage("pdf_assembly", "started", generation.id, request_id)
        merge_pdfs(source_paths=source_paths, output_path=final_path)
        add_page_numbers(pdf_path=final_path, skip_pages=skip_pages)
        page_count = _count_pages(final_path)
        add_metadata(
            pdf_path=final_path,
            title=cover_title,
            subject=document.context,
            author=request.teacher_name,
        )
        _validate_limits(final_path, page_count, config)
        _log_stage(
            "pdf_assembly",
            "completed",
            generation.id,
            request_id,
            duration_ms=_duration_ms(assembly_started),
        )
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        _log_stage(
            "pdf_export",
            "failed",
            generation.id,
            request_id,
            duration_ms=duration_ms,
        )
        pdf_export_telemetry.record_export(duration_ms=duration_ms, status="failed")
        cleanup_files(cleanup_paths + [final_path])
        raise

    duration_ms = int((time.perf_counter() - started) * 1000)
    _log_stage("pdf_export", "completed", generation.id, request_id, duration_ms=duration_ms)
    pdf_export_telemetry.record_export(duration_ms=duration_ms, status="completed")
    filename = _slugify(cover_title) + ".pdf"
    return PDFExportResult(
        pdf_path=final_path,
        filename=filename,
        file_size_bytes=final_path.stat().st_size,
        page_count=page_count,
        generation_time_ms=duration_ms,
        cleanup_paths=cleanup_paths + [final_path],
    )


def _log_stage(
    stage: str,
    status: str,
    generation_id: str,
    request_id: str | None,
    *,
    duration_ms: int | None = None,
) -> None:
    extra: dict[str, object] = {
        "generation_id": generation_id,
        "request_id": request_id or "-",
        "stage": stage,
        "status": status,
    }
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
        if status != "started":
            pdf_export_telemetry.record_stage(
                stage,
                duration_ms=duration_ms,
                status=status,
            )
    logger.info("PDF export stage", extra=extra)


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _validate_limits(pdf_path: Path, page_count: int, config: PDFExportConfig) -> None:
    file_size = pdf_path.stat().st_size
    if file_size > config.max_file_size_bytes:
        raise RuntimeError(
            f"Generated PDF exceeds size limit ({file_size} > {config.max_file_size_bytes})"
        )
    if page_count > config.max_page_count:
        raise RuntimeError(
            f"Generated PDF exceeds page limit ({page_count} > {config.max_page_count})"
        )


def _count_pages(pdf_path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(pdf_path)).pages)


def _slugify(text: str) -> str:
    value = "".join(char.lower() if char.isalnum() else "-" for char in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value or "lesson"
