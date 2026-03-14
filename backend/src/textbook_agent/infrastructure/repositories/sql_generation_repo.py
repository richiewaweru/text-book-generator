from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.infrastructure.database.models import GenerationModel


class SqlGenerationRepository(GenerationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, generation: Generation) -> Generation:
        model = GenerationModel(
            id=generation.id,
            user_id=generation.user_id,
            subject=generation.subject,
            context=generation.context,
            mode=generation.mode.value,
            status=generation.status,
            source_generation_id=generation.source_generation_id,
            created_at=generation.created_at,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update_status(
        self,
        generation_id: str,
        status: str,
        output_path: str | None = None,
        error: str | None = None,
        quality_passed: bool | None = None,
        generation_time_seconds: float | None = None,
    ) -> None:
        stmt = select(GenerationModel).where(GenerationModel.id == generation_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        model.status = status
        if output_path is not None:
            model.output_path = output_path
        if error is not None:
            model.error = error
        if quality_passed is not None:
            model.quality_passed = quality_passed
        if generation_time_seconds is not None:
            model.generation_time_seconds = generation_time_seconds
        if status in ("completed", "failed"):
            model.completed_at = datetime.now(timezone.utc)
        await self._session.commit()

    async def find_by_id(self, generation_id: str) -> Generation | None:
        stmt = select(GenerationModel).where(GenerationModel.id == generation_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_user(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> list[Generation]:
        stmt = (
            select(GenerationModel)
            .where(GenerationModel.user_id == user_id)
            .order_by(GenerationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(model: GenerationModel) -> Generation:
        return Generation(
            id=model.id,
            user_id=model.user_id,
            subject=model.subject,
            context=model.context or "",
            mode=model.mode,
            status=model.status,
            output_path=model.output_path,
            error=model.error,
            quality_passed=model.quality_passed,
            generation_time_seconds=model.generation_time_seconds,
            source_generation_id=model.source_generation_id,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )
