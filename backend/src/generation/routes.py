from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import core.events as core_events
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from core.auth.jwt_handler import JWTHandler
from core.auth.middleware import get_current_user
from core.dependencies import (
    get_jwt_handler,
    get_settings,
    get_student_profile_repository,
    get_user_repository,
)
from core.entities.user import User
from core.ports.student_profile_repository import StudentProfileRepository
from core.ports.user_repository import UserRepository
from generation import service as generation_service
from generation.dependencies import (
    get_document_repository,
    get_generation_engine,
    get_generation_repository,
)
from generation.dtos import GenerationAcceptedResponse, GenerationRequest
from generation.ports.document_repository import DocumentRepository
from generation.ports.generation_repository import GenerationRepository
from pipeline.adapter import run_pipeline_streaming
from pipeline.api import PipelineCommand as _PipelineCommand
from pipeline.block_generate import (
    BlockGenerateRequest,
    BlockGenerateResponse,
    run_block_generation,
)
from telemetry.dependencies import get_report_repository
from telemetry.ports.generation_report_repository import GenerationReportRepository

PipelineCommand = _PipelineCommand

router = APIRouter(prefix="/api/v1", tags=["generation"])

# Re-export the service-layer symbols that the route tests exercise directly.
event_bus = core_events.event_bus
_SSE_KEEPALIVE_TIMEOUT_SECONDS = generation_service._SSE_KEEPALIVE_TIMEOUT_SECONDS
_persist_failed_generation_state = generation_service._persist_failed_generation_state
_generation_job_timeout = generation_service._generation_job_timeout


class _PatchedPipelineEngine:
    async def run_streaming(self, command, on_event=None):
        return await run_pipeline_streaming(command, on_event=on_event)


@router.post("/blocks/generate", response_model=BlockGenerateResponse)
async def generate_block(
    body: BlockGenerateRequest,
    current_user: User = Depends(get_current_user),
) -> BlockGenerateResponse:
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


@router.post("/generations", status_code=202, response_model=GenerationAcceptedResponse)
async def create_generation(
    req: GenerationRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
    engine=Depends(get_generation_engine),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
):
    (
        effective_subject,
        effective_context,
        effective_mode,
        effective_template_id,
        effective_preset_id,
        effective_section_count,
        effective_section_plans,
        planning_spec_json,
    ) = generation_service._effective_generation_payload(req)

    profile = await profile_repo.find_by_user_id(current_user.id)
    return await generation_service.enqueue_generation(
        current_user=current_user,
        profile=profile,
        engine=engine,
        gen_repo=gen_repo,
        document_repo=document_repo,
        report_repo=report_repo,
        subject=effective_subject,
        context=effective_context,
        mode=effective_mode,
        template_id=effective_template_id,
        preset_id=effective_preset_id,
        section_count=effective_section_count,
        section_plans=effective_section_plans,
        planning_spec_json=planning_spec_json,
    )


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
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    return generation_service._detail_item(generation)


@router.get("/generations/{generation_id}/document")
async def get_generation_document(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if not generation.document_path:
        raise HTTPException(status_code=404, detail="Document not found")
    document = await document_repo.load_document(generation.document_path)
    return document.model_dump(mode="json", exclude_none=True)


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

    async def stream() -> AsyncIterator[str]:
        async def emit_event_payloads(event_payload: dict) -> AsyncIterator[str]:
            yield generation_service._sse_payload(event_payload)
            for progress_update in generation_service._progress_updates_for_event(
                event_payload
            ):
                yield generation_service._sse_payload(progress_update)

        queue = core_events.event_bus.subscribe(generation_id)
        try:
            current = await gen_repo.find_by_id(generation_id)
            while not queue.empty():
                event = queue.get_nowait()
                async for payload in emit_event_payloads(event):
                    yield payload
                if event.get("type") in {"complete", "error"}:
                    return

            if current is not None and current.status == "completed":
                terminal = generation_service._complete_event(generation_id).model_dump(
                    mode="json",
                    exclude_none=True,
                )
                async for payload in emit_event_payloads(terminal):
                    yield payload
                return
            if current is not None and current.status == "failed":
                terminal = generation_service._error_event(
                    generation_id,
                    current.error or "Generation failed",
                ).model_dump(mode="json", exclude_none=True)
                async for payload in emit_event_payloads(terminal):
                    yield payload
                return

            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=_SSE_KEEPALIVE_TIMEOUT_SECONDS,
                    )
                except TimeoutError:
                    current = await gen_repo.find_by_id(generation_id)
                    if current is not None and current.status == "completed":
                        yield generation_service._sse_payload(
                            generation_service._complete_event(generation_id).model_dump(
                                mode="json",
                                exclude_none=True,
                            )
                        )
                        return
                    if current is not None and current.status == "failed":
                        yield generation_service._sse_payload(
                            generation_service._error_event(
                                generation_id,
                                current.error or "Generation failed",
                            ).model_dump(mode="json", exclude_none=True)
                        )
                        return
                    yield ": keep-alive\n\n"
                    continue

                async for payload in emit_event_payloads(event):
                    yield payload
                if event["type"] in {"complete", "error"}:
                    break
        finally:
            core_events.event_bus.unsubscribe(generation_id, queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
