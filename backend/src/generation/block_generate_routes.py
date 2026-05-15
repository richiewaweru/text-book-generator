from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.middleware import get_current_user
from core.database.models import EditableLessonModel
from core.database.session import get_async_session
from core.entities.user import User
from generation.block_generate import (
    BlockGenerateRequest,
    BlockGenerateResponse,
    run_block_generation,
)

block_generate_router = APIRouter()


@block_generate_router.post("/blocks/generate", response_model=BlockGenerateResponse)
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
