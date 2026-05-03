from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core.auth.middleware import get_current_user
from core.entities.user import User
from v3_blueprint.models import ProductionBlueprint
from v3_execution.runtime.runner import sse_event_stream

from generation.v3_studio.agents import (
    adjust_production_blueprint,
    extract_signals,
    generate_production_blueprint,
    get_clarifications,
)
from generation.v3_studio.dtos import (
    AdjustBlueprintRequest,
    BlueprintPreviewDTO,
    ClarifyRequest,
    GenerateBlueprintRequest,
    V3ClarificationQuestion,
    V3GenerateStartRequest,
    V3GenerateStartResponse,
    V3InputForm,
    V3SignalSummary,
)
from generation.v3_studio.preview_mapper import blueprint_to_preview_dto
from generation.v3_studio.session_store import v3_studio_store

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
    bp = await generate_production_blueprint(
        signals=body.signals,
        form=body.form,
        clarification_answers=body.clarification_answers,
        trace_id=str(uuid.uuid4()),
    )
    blueprint_id = str(uuid.uuid4())
    template_id = "diagram-led"
    await v3_studio_store.put_blueprint(current_user.id, blueprint_id, bp, template_id)
    return blueprint_to_preview_dto(blueprint_id=blueprint_id, blueprint=bp, template_id=template_id)


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
        current_user.id, body.blueprint_id, revised, stored.template_id
    )
    return blueprint_to_preview_dto(
        blueprint_id=body.blueprint_id,
        blueprint=revised,
        template_id=stored.template_id,
    )


async def _pump_sse_to_queue(
    queue: asyncio.Queue[str | None],
    *,
    blueprint: ProductionBlueprint,
    generation_id: str,
    blueprint_id: str,
    template_id: str,
) -> None:
    try:
        async for chunk in sse_event_stream(
            blueprint=blueprint,
            generation_id=generation_id,
            blueprint_id=blueprint_id,
            template_id=template_id,
            trace_id=generation_id,
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

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    await v3_studio_store.register_generation_stream(
        user_id=current_user.id,
        generation_id=body.generation_id,
        queue=queue,
    )
    asyncio.create_task(
        _pump_sse_to_queue(
            queue,
            blueprint=blueprint,
            generation_id=body.generation_id,
            blueprint_id=body.blueprint_id,
            template_id=template_id,
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


__all__ = ["v3_studio_router"]
