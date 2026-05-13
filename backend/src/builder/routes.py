"""Server persistence for teacher-owned Builder lessons (Phase 2)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.middleware import get_current_user
from core.database.models import EditableLessonModel, GenerationModel
from core.database.session import get_async_session
from core.entities.user import User
from pipeline.contracts import get_component_registry_entry

router = APIRouter(prefix="/api/v1/builder", tags=["builder"])

_VALID_SOURCES = {"manual", "v3_generation", "template"}
_MAX_DOCUMENT_BYTES = 5 * 1024 * 1024


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clone_json_tree(value: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(json.dumps(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Document must be valid JSON") from exc


def _validate_lesson_document_shape(document: dict[str, Any]) -> None:
    payload = _clone_json_tree(document)
    payload_bytes = len(json.dumps(payload).encode("utf-8"))
    if payload_bytes > _MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Document payload exceeds {_MAX_DOCUMENT_BYTES} bytes",
        )

    version = payload.get("version")
    if not isinstance(version, int):
        raise HTTPException(status_code=422, detail="LessonDocument.version must be an integer")

    lesson_id = payload.get("id")
    if not isinstance(lesson_id, str) or not lesson_id.strip():
        raise HTTPException(status_code=422, detail="LessonDocument.id must be a non-empty string")

    sections = payload.get("sections")
    if not isinstance(sections, list):
        raise HTTPException(status_code=422, detail="LessonDocument.sections must be a list")

    blocks = payload.get("blocks")
    if not isinstance(blocks, dict):
        raise HTTPException(status_code=422, detail="LessonDocument.blocks must be an object")

    media = payload.get("media")
    if media is None or not isinstance(media, dict):
        raise HTTPException(status_code=422, detail="LessonDocument.media must be an object")

    known_block_ids = set(blocks.keys())
    for block_id, raw_block in blocks.items():
        if not isinstance(block_id, str) or not block_id.strip():
            raise HTTPException(status_code=422, detail="Block ids must be non-empty strings")
        if not isinstance(raw_block, dict):
            raise HTTPException(status_code=422, detail=f"Block '{block_id}' must be an object")

        component_id = raw_block.get("component_id")
        if not isinstance(component_id, str) or not component_id.strip():
            raise HTTPException(
                status_code=422,
                detail=f"Block '{block_id}' is missing a valid component_id",
            )
        if get_component_registry_entry(component_id) is None:
            raise HTTPException(status_code=400, detail=f"Unknown component_id: {component_id}")

        if "content" not in raw_block:
            raise HTTPException(status_code=422, detail=f"Block '{block_id}' is missing content")

    for section in sections:
        if not isinstance(section, dict):
            raise HTTPException(status_code=422, detail="Each section must be an object")
        block_ids = section.get("block_ids")
        if not isinstance(block_ids, list):
            raise HTTPException(status_code=422, detail="Section block_ids must be a list")
        for block_id in block_ids:
            if not isinstance(block_id, str) or not block_id.strip():
                raise HTTPException(status_code=422, detail="Section block_ids must be non-empty strings")
            if block_id not in known_block_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Section references missing block id: {block_id}",
                )


def _normalize_document_for_storage(
    document: dict[str, Any],
    *,
    lesson_id: str,
    title: str,
    now_iso: str,
    created_at_value: str | None = None,
) -> dict[str, Any]:
    normalized = _clone_json_tree(document)
    normalized["id"] = lesson_id
    normalized["title"] = title
    if created_at_value:
        normalized["created_at"] = created_at_value
    else:
        normalized.setdefault("created_at", now_iso)
    normalized["updated_at"] = now_iso
    return normalized


class BuilderLessonCreateRequest(BaseModel):
    title: str | None = None
    source_generation_id: str | None = None
    source_type: Literal["manual", "v3_generation", "template"] = "manual"
    document: dict[str, Any] = Field(..., description="LessonDocument JSON payload")


class BuilderLessonUpdateRequest(BaseModel):
    title: str | None = None
    document: dict[str, Any] = Field(..., description="LessonDocument JSON payload")


class BuilderLessonListItem(BaseModel):
    id: str
    source_generation_id: str | None
    source_type: str
    title: str
    created_at: datetime
    updated_at: datetime


class BuilderLessonDetailResponse(BuilderLessonListItem):
    document: dict[str, Any]


def _to_list_item(model: EditableLessonModel) -> BuilderLessonListItem:
    return BuilderLessonListItem(
        id=model.id,
        source_generation_id=model.source_generation_id,
        source_type=model.source_type,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_detail(model: EditableLessonModel) -> BuilderLessonDetailResponse:
    return BuilderLessonDetailResponse(
        **_to_list_item(model).model_dump(),
        document=model.document_json,
    )


def _resolved_title(explicit: str | None, document: dict[str, Any], default: str = "Untitled lesson") -> str:
    title = (explicit or "").strip()
    if title:
        return title
    candidate = document.get("title")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    return default


async def _owned_lesson_or_404(
    session: AsyncSession,
    *,
    lesson_id: str,
    user_id: str,
) -> EditableLessonModel:
    result = await session.execute(
        select(EditableLessonModel).where(
            EditableLessonModel.id == lesson_id,
            EditableLessonModel.user_id == user_id,
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return model


@router.post("/lessons", response_model=BuilderLessonDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_builder_lesson(
    body: BuilderLessonCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> BuilderLessonDetailResponse:
    if body.source_type not in _VALID_SOURCES:
        raise HTTPException(status_code=422, detail=f"Unsupported source_type: {body.source_type}")
    if body.source_type == "v3_generation" and not body.source_generation_id:
        raise HTTPException(status_code=422, detail="source_generation_id is required for v3_generation")

    if body.source_generation_id:
        generation_result = await session.execute(
            select(GenerationModel.id).where(
                GenerationModel.id == body.source_generation_id,
                GenerationModel.user_id == current_user.id,
            )
        )
        if generation_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Source generation not found")

    _validate_lesson_document_shape(body.document)

    now = _utc_naive_now()
    now_iso = now.isoformat()
    lesson_id = str(uuid.uuid4())
    title = _resolved_title(body.title, body.document)
    document_json = _normalize_document_for_storage(
        body.document,
        lesson_id=lesson_id,
        title=title,
        now_iso=now_iso,
    )

    model = EditableLessonModel(
        id=lesson_id,
        user_id=current_user.id,
        source_generation_id=body.source_generation_id,
        source_type=body.source_type,
        title=title,
        document_json=document_json,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.commit()
    return _to_detail(model)


@router.get("/lessons", response_model=list[BuilderLessonListItem])
async def list_builder_lessons(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[BuilderLessonListItem]:
    result = await session.execute(
        select(EditableLessonModel)
        .where(EditableLessonModel.user_id == current_user.id)
        .order_by(EditableLessonModel.updated_at.desc())
    )
    return [_to_list_item(model) for model in result.scalars().all()]


@router.get("/lessons/{lesson_id}", response_model=BuilderLessonDetailResponse)
async def get_builder_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> BuilderLessonDetailResponse:
    model = await _owned_lesson_or_404(session, lesson_id=lesson_id, user_id=current_user.id)
    return _to_detail(model)


@router.put("/lessons/{lesson_id}", response_model=BuilderLessonDetailResponse)
async def update_builder_lesson(
    lesson_id: str,
    body: BuilderLessonUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> BuilderLessonDetailResponse:
    model = await _owned_lesson_or_404(session, lesson_id=lesson_id, user_id=current_user.id)
    _validate_lesson_document_shape(body.document)

    now = _utc_naive_now()
    now_iso = now.isoformat()
    title = _resolved_title(body.title, body.document, default=model.title)
    created_at_value = model.document_json.get("created_at") if isinstance(model.document_json, dict) else None
    document_json = _normalize_document_for_storage(
        body.document,
        lesson_id=lesson_id,
        title=title,
        now_iso=now_iso,
        created_at_value=created_at_value if isinstance(created_at_value, str) else None,
    )

    model.title = title
    model.document_json = document_json
    model.updated_at = now
    await session.commit()
    return _to_detail(model)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_builder_lesson(
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    model = await _owned_lesson_or_404(session, lesson_id=lesson_id, user_id=current_user.id)
    await session.delete(model)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

