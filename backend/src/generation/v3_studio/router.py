from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from starlette.background import BackgroundTask

from core.auth.jwt_handler import JWTHandler
from core.auth.middleware import get_current_user
from core.dependencies import get_jwt_handler, get_settings
from core.entities.user import User
from v3_blueprint.models import ProductionBlueprint
from v3_execution.runtime.runner import sse_event_stream

from generation.v3_studio.agents import (
    adjust_production_blueprint,
    extract_signals,
    generate_production_blueprint,
    get_clarifications,
)
from generation.pdf_export.cleanup import cleanup_files
from generation.pdf_export.service import PDFExportRequest, export_v3_studio_pdf
from generation.v3_studio.dtos import (
    AdjustBlueprintRequest,
    BlueprintPreviewDTO,
    ClarifyRequest,
    GenerateBlueprintRequest,
    V3ClarificationQuestion,
    V3GenerateStartRequest,
    V3GenerateStartResponse,
    V3InputForm,
    V3PdfExportRequest,
    V3SignalSummary,
)
from generation.v3_studio.preview_mapper import blueprint_to_preview_dto
from generation.v3_studio.session_store import v3_studio_store
from telemetry.dependencies import get_v3_trace_repository
from telemetry.service import telemetry_monitor
from telemetry.v3_trace.repository import V3TraceRepository
from telemetry.v3_trace.writer import V3TraceWriter

logger = logging.getLogger(__name__)

v3_studio_router = APIRouter(prefix="/v3", tags=["v3-studio"])


@v3_studio_router.post("/signals", response_model=V3SignalSummary)
async def post_signals(
    body: V3InputForm,
    current_user: User = Depends(get_current_user),
) -> V3SignalSummary:
    _ = current_user
    return await extract_signals(body, trace_id=str(uuid.uuid4()))


@v3_studio_router.post("/clarify", response_model=list[V3ClarificationQuestion])
async def post_clarify(
    body: ClarifyRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return await get_clarifications(body.signals, body.form, trace_id=str(uuid.uuid4()))


@v3_studio_router.post("/blueprint", response_model=BlueprintPreviewDTO)
async def post_blueprint(
    body: GenerateBlueprintRequest,
    current_user: User = Depends(get_current_user),
) -> BlueprintPreviewDTO:
    try:
        bp = await generate_production_blueprint(
            signals=body.signals,
            form=body.form,
            clarification_answers=body.clarification_answers,
            trace_id=str(uuid.uuid4()),
        )
        blueprint_id = str(uuid.uuid4())
        template_id = "guided-concept-path"
        await v3_studio_store.put_blueprint(
            current_user.id,
            blueprint_id,
            bp,
            template_id,
            form=body.form,
        )
        return blueprint_to_preview_dto(
            blueprint_id=blueprint_id,
            blueprint=bp,
            template_id=template_id,
            form=body.form,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Blueprint generation failed user=%s error=%s",
            current_user.id,
            str(exc)[:400],
        )
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {str(exc)[:400]}",
        ) from exc


@v3_studio_router.post("/blueprint/adjust", response_model=BlueprintPreviewDTO)
async def post_blueprint_adjust(
    body: AdjustBlueprintRequest,
    current_user: User = Depends(get_current_user),
) -> BlueprintPreviewDTO:
    stored = await v3_studio_store.get_blueprint(current_user.id, body.blueprint_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    revised = await adjust_production_blueprint(
        stored.blueprint,
        body.adjustment,
        trace_id=str(uuid.uuid4()),
    )
    await v3_studio_store.put_blueprint(
        current_user.id,
        body.blueprint_id,
        revised,
        stored.template_id,
        form=stored.form,
    )
    return blueprint_to_preview_dto(
        blueprint_id=body.blueprint_id,
        blueprint=revised,
        template_id=stored.template_id,
        form=stored.form,
    )


async def _pump_sse_to_queue(
    queue: asyncio.Queue[str | None],
    *,
    blueprint: ProductionBlueprint,
    generation_id: str,
    blueprint_id: str,
    template_id: str,
    trace_writer: V3TraceWriter | None = None,
) -> None:
    try:
        async for chunk in sse_event_stream(
            blueprint=blueprint,
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            template_id=template_id,
            trace_id=trace_writer.trace_id if trace_writer is not None else generation_id,
            trace_writer=trace_writer,
        ):
            await queue.put(chunk)
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001
        pass
    finally:
        await queue.put(None)


@v3_studio_router.post("/generate/start", response_model=V3GenerateStartResponse)
async def post_v3_generate_start(
    body: V3GenerateStartRequest,
    current_user: User = Depends(get_current_user),
    trace_repo: V3TraceRepository = Depends(get_v3_trace_repository),
) -> V3GenerateStartResponse:
    existing = await v3_studio_store.get_queue(body.generation_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="generation_id already started")

    stored = await v3_studio_store.get_blueprint(current_user.id, body.blueprint_id)
    template_id = body.template_id
    blueprint: ProductionBlueprint | None = None
    if stored is not None:
        blueprint = stored.blueprint
        template_id = stored.template_id
    elif body.blueprint is not None:
        blueprint = ProductionBlueprint.model_validate(body.blueprint)
    else:
        raise HTTPException(status_code=404, detail="Blueprint not found for user")

    trace_id = str(uuid.uuid4())
    trace_writer = V3TraceWriter(
        repository=trace_repo,
        trace_id=trace_id,
        generation_id=body.generation_id,
    )
    try:
        await trace_writer.start_run(
            user_id=current_user.id,
            blueprint_id=body.blueprint_id,
            template_id=template_id,
            title=blueprint.metadata.title,
            subject=blueprint.metadata.subject,
        )
        component_count = sum(len(section.components) for section in blueprint.sections)
        visual_required_count = sum(1 for section in blueprint.sections if section.visual_required)
        lenses = [lens.lens_id for lens in blueprint.applied_lenses]
        await trace_writer.record_blueprint_snapshot(
            blueprint_id=body.blueprint_id,
            template_id=template_id,
            section_count=len(blueprint.sections),
            section_ids=[section.section_id for section in blueprint.sections],
            component_count=component_count,
            visual_required_count=visual_required_count,
            question_count=len(blueprint.question_plan),
            lenses=lenses,
        )
        await telemetry_monitor.initialise_v3_recorder(
            generation_id=body.generation_id,
            user_id=str(current_user.id),
            blueprint_title=blueprint.metadata.title,
            subject=blueprint.metadata.subject,
            template_id=template_id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "v3 trace init failed generation_id=%s trace_id=%s error=%s",
            body.generation_id,
            trace_id,
            str(exc)[:400],
        )
        raise HTTPException(
            status_code=500,
            detail="Could not start generation because telemetry could not be initialized.",
        ) from exc

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    await v3_studio_store.register_generation_stream(
        user_id=current_user.id,
        generation_id=body.generation_id,
        blueprint_id=body.blueprint_id,
        queue=queue,
    )
    asyncio.create_task(
        _pump_sse_to_queue(
            queue,
            blueprint=blueprint,
            generation_id=body.generation_id,
            blueprint_id=body.blueprint_id,
            template_id=template_id,
            trace_writer=trace_writer,
        )
    )
    return V3GenerateStartResponse(generation_id=body.generation_id)


@v3_studio_router.get("/generations/{generation_id}/events")
async def get_v3_generation_events(
    generation_id: str,
    current_user: User = Depends(get_current_user),
):
    if not await v3_studio_store.owns_generation(current_user.id, generation_id):
        raise HTTPException(status_code=404, detail="Generation stream not found")

    queue = await v3_studio_store.get_queue(generation_id)
    if queue is None:
        raise HTTPException(status_code=404, detail="Generation stream not found")
    stored = await v3_studio_store.get_blueprint_for_generation(generation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    await telemetry_monitor.initialise_v3_recorder(
        generation_id=generation_id,
        user_id=str(current_user.id),
        blueprint_title=stored.blueprint.metadata.title,
        subject=stored.blueprint.metadata.subject,
        template_id=stored.template_id,
    )

    async def event_generator():
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await v3_studio_store.cleanup_generation(generation_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@v3_studio_router.get("/generations/{generation_id}/blueprint", response_model=BlueprintPreviewDTO)
async def get_v3_generation_blueprint(
    generation_id: str,
    current_user: User = Depends(get_current_user),
) -> BlueprintPreviewDTO:
    owner = await v3_studio_store.get_generation_owner(generation_id)
    if owner != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    blueprint_id = await v3_studio_store.get_blueprint_id_for_generation(generation_id)
    stored = await v3_studio_store.get_blueprint_for_generation(generation_id)
    if stored is None or blueprint_id is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    return blueprint_to_preview_dto(
        blueprint_id=blueprint_id,
        blueprint=stored.blueprint,
        template_id=stored.template_id,
        form=stored.form,
    )


@v3_studio_router.get("/generations/{generation_id}/print-snapshot")
async def get_v3_print_snapshot(
    generation_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    if not await v3_studio_store.owns_generation(current_user.id, generation_id):
        raise HTTPException(status_code=404, detail="Generation not found")
    snap = await v3_studio_store.get_print_snapshot(generation_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Print snapshot not available")
    return snap


@v3_studio_router.post("/generations/{generation_id}/export/pdf")
async def post_v3_export_pdf(
    generation_id: str,
    body: V3PdfExportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
):
    owner = await v3_studio_store.get_generation_owner(generation_id)
    if owner != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    stored = await v3_studio_store.get_blueprint_for_generation(generation_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    await v3_studio_store.put_print_snapshot(
        generation_id,
        {"sections": body.pack_sections, "template_id": stored.template_id},
    )

    auth_token = jwt_handler.create_access_token(current_user.id, current_user.email)
    pdf_request = PDFExportRequest(
        school_name=body.school_name,
        teacher_name=body.teacher_name,
        date=body.date,
        include_toc=body.include_toc,
        include_answers=body.include_answers,
    )
    try:
        result = await export_v3_studio_pdf(
            generation_id=generation_id,
            user_id=current_user.id,
            title=stored.blueprint.metadata.title,
            subject=stored.blueprint.metadata.subject,
            template_id=stored.template_id,
            auth_token=auth_token,
            request=pdf_request,
            settings=get_settings(),
            request_id=getattr(request.state, "request_id", None),
        )
    except Exception:
        await v3_studio_store.delete_print_snapshot(generation_id)
        raise
    await v3_studio_store.delete_print_snapshot(generation_id)

    async def _cleanup() -> None:
        cleanup_files(result.cleanup_paths)

    return FileResponse(
        path=result.pdf_path,
        media_type="application/pdf",
        filename=result.filename,
        background=BackgroundTask(_cleanup),
        headers={
            "X-Page-Count": str(result.page_count),
            "X-File-Size": str(result.file_size_bytes),
            "X-Generation-Time-Ms": str(result.generation_time_ms),
        },
    )


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    report = trace.get("report") or {}
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "trace_id": trace.get("trace_id"),
        "generation_id": trace.get("generation_id"),
        "status": trace.get("status"),
        "title": trace.get("title"),
        "subject": trace.get("subject"),
        "template_id": trace.get("template_id"),
        "booklet_status": report.get("booklet_status"),
        "draft_available": report.get("draft_available"),
        "final_available": report.get("final_available"),
        "classroom_ready": report.get("classroom_ready"),
        "export_allowed": report.get("export_allowed"),
        "summary": summary,
        "events": trace.get("events", []),
    }


@v3_studio_router.get("/generations/{generation_id}/trace")
async def get_v3_generation_trace(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    trace_repo: V3TraceRepository = Depends(get_v3_trace_repository),
) -> dict[str, Any]:
    run = await trace_repo.get_run_by_generation(generation_id)
    if run is None or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Trace not found")
    trace = await trace_repo.get_full_trace(run.trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return _compact_trace(trace)


@v3_studio_router.get("/traces/{trace_id}")
async def get_v3_trace_by_id(
    trace_id: str,
    current_user: User = Depends(get_current_user),
    trace_repo: V3TraceRepository = Depends(get_v3_trace_repository),
) -> dict[str, Any]:
    run = await trace_repo.get_run(trace_id)
    if run is None or run.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Trace not found")
    trace = await trace_repo.get_full_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return _compact_trace(trace)


__all__ = ["v3_studio_router"]
