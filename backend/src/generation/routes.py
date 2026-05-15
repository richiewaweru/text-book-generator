from __future__ import annotations

import asyncio

import core.events as core_events
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from core.auth.jwt_handler import JWTHandler
from core.auth.middleware import get_current_user
from core.database.models import EditableLessonModel, GenerationModel
from core.database.session import get_async_session
from core.dependencies import (
    get_jwt_handler,
    get_settings,
    get_user_repository,
)
from core.entities.user import User
from core.ports.user_repository import UserRepository
from pydantic import BaseModel

from generation import service as generation_service
from generation.dependencies import (
    get_document_repository,
    get_generation_repository,
)
from generation.pdf_export.cleanup import cleanup_files
from generation.pdf_export.service import PDFExportRequest, export_generation_pdf
from generation.v3_studio.router import v3_studio_router
from generation.ports.document_repository import DocumentRepository
from generation.ports.generation_repository import GenerationRepository
from pipeline.adapter import run_pipeline_streaming
from pipeline.api import PipelineCommand as _PipelineCommand
from generation.block_generate import (
    BlockGenerateRequest,
    BlockGenerateResponse,
    run_block_generation,
)
from telemetry.dependencies import get_report_repository
from telemetry.ports.generation_report_repository import GenerationReportRepository
from v3_blueprint.models import ProductionBlueprint
from v3_execution.runtime.runner import sse_event_stream

PipelineCommand = _PipelineCommand


class V3GenerateRequest(BaseModel):
    generation_id: str
    blueprint_id: str
    template_id: str = "guided-concept-path"
    blueprint: dict

router = APIRouter(prefix="/api/v1", tags=["generation"])
router.include_router(v3_studio_router)

# Re-export the service-layer symbols that the route tests exercise directly.
event_bus = core_events.event_bus
_SSE_KEEPALIVE_TIMEOUT_SECONDS = generation_service._SSE_KEEPALIVE_TIMEOUT_SECONDS
_persist_failed_generation_state = generation_service._persist_failed_generation_state
_generation_job_timeout = generation_service._generation_job_timeout
_ASYNCIO_PATCH_POINT = asyncio


class _PatchedPipelineEngine:
    async def run_streaming(self, command, on_event=None):
        return await run_pipeline_streaming(command, on_event=on_event)


@router.post("/blocks/generate", response_model=BlockGenerateResponse)
async def generate_block(
    body: BlockGenerateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> BlockGenerateResponse:
    if body.lesson_id:
        lesson_lookup = await session.execute(
            select(EditableLessonModel.id).where(
                EditableLessonModel.id == body.lesson_id,
                EditableLessonModel.user_id == current_user.id,
            )
        )
        if lesson_lookup.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
    content = await run_block_generation(body, user_id=current_user.id)
    return BlockGenerateResponse(content=content)


async def _run_generation_job(
    generation,
    command,
    gen_repo,
    document_repo,
    report_repo,
    initial_document,
):
    original_persist_failed_generation_state = (
        generation_service._persist_failed_generation_state
    )
    original_generation_job_timeout = generation_service._generation_job_timeout
    try:
        generation_service._persist_failed_generation_state = (
            _persist_failed_generation_state
        )
        generation_service._generation_job_timeout = _generation_job_timeout
        return await generation_service._run_generation_job(
            generation,
            command,
            _PatchedPipelineEngine(),
            gen_repo,
            document_repo,
            report_repo,
            initial_document,
        )
    finally:
        generation_service._persist_failed_generation_state = (
            original_persist_failed_generation_state
        )
        generation_service._generation_job_timeout = original_generation_job_timeout


@router.get("/generations")
async def list_generations(
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    limit: int = get_settings().default_pagination_limit,
    offset: int = 0,
):
    generations = await gen_repo.list_by_user(current_user.id, limit=limit, offset=offset)
    return [generation_service._history_item(generation) for generation in generations]


@router.get("/generations/{generation_id}")
async def get_generation_detail(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    try:
        report = await report_repo.load_report(generation_id)
    except (FileNotFoundError, KeyError):
        report = None
    return generation_service._detail_item(generation, report=report)


@router.get("/generations/{generation_id}/document")
async def get_generation_document(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    session: AsyncSession = Depends(get_async_session),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")

    model = await session.get(GenerationModel, generation_id)
    if model is not None and model.user_id == current_user.id and isinstance(model.document_json, dict):
        document_json = model.document_json
        if document_json.get("kind") == "v3_booklet_pack":
            sections = document_json.get("sections")
            if isinstance(sections, list) and sections:
                return document_json

    document_ref = generation.document_path or generation.id
    try:
        document = await document_repo.load_document(document_ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    return document.model_dump(mode="json", exclude_none=True)


@router.post("/generations/{generation_id}/export/pdf")
async def export_generation_pdf_route(
    generation_id: str,
    body: PDFExportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if generation.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="PDF export is only available for completed generations",
        )

    document_ref = generation.document_path or generation.id
    try:
        document = await document_repo.load_document(document_ref)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc

    auth_token = jwt_handler.create_access_token(current_user.id, current_user.email)
    result = await export_generation_pdf(
        generation=generation,
        document=document,
        auth_token=auth_token,
        request=body,
        settings=get_settings(),
        request_id=getattr(request.state, "request_id", None),
    )
    return FileResponse(
        path=result.pdf_path,
        media_type="application/pdf",
        filename=result.filename,
        headers={
            "X-Page-Count": str(result.page_count),
            "X-File-Size": str(result.file_size_bytes),
            "X-Generation-Time-Ms": str(result.generation_time_ms),
        },
        background=BackgroundTask(cleanup_files, result.cleanup_paths),
    )


@router.get("/generations/{generation_id}/events")
async def get_generation_events(
    generation_id: str,
    request: Request,
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    user_repo: UserRepository = Depends(get_user_repository),
):
    current_user = await generation_service._stream_user_from_token(
        request,
        jwt_handler,
        user_repo,
    )
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")

    return StreamingResponse(
        generation_service._stream_generation_events(
            generation_id=generation_id,
            gen_repo=gen_repo,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v3/generate")
async def trigger_v3_generation(
    body: V3GenerateRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    blueprint = ProductionBlueprint.model_validate(body.blueprint)

    return StreamingResponse(
        sse_event_stream(
            blueprint=blueprint,
            generation_id=body.generation_id,
            blueprint_id=body.blueprint_id,
            template_id=body.template_id,
            trace_id=body.generation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

