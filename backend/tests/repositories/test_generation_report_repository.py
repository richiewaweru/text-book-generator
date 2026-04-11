from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database.models import GenerationModel, UserModel
from generation.entities.generation import Generation
from generation.repositories.sql_generation_repo import SqlGenerationRepository
from telemetry.dtos import GenerationReport, GenerationReportSummary
from telemetry.repositories.sql_generation_report_repo import (
    SqlGenerationReportRepository,
)


TEST_USER_ID = "test-user-001"


@pytest.fixture
async def session(db_session: AsyncSession):
    db_session.add(
        UserModel(
            id=TEST_USER_ID,
            email="test@example.com",
            name="Test User",
        )
    )
    await db_session.commit()
    yield db_session


@pytest.fixture
def generation_repo(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> SqlGenerationRepository:
    return SqlGenerationRepository(db_session_factory)


@pytest.fixture
def report_repo(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> SqlGenerationReportRepository:
    return SqlGenerationReportRepository(db_session_factory)


def _generation(generation_id: str = "gen-report") -> Generation:
    return Generation(
        id=generation_id,
        user_id=TEST_USER_ID,
        subject="Calculus",
        context="Explain limits",
        requested_template_id="guided-concept-path",
        requested_preset_id="blue-classroom",
    )


def _report(generation_id: str = "gen-report") -> GenerationReport:
    return GenerationReport(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="running",
        outcome="partial",
        section_count=2,
        summary=GenerationReportSummary(),
    )


class TestSqlGenerationReportRepository:
    async def test_save_and_load_report_round_trip(
        self,
        generation_repo: SqlGenerationRepository,
        report_repo: SqlGenerationReportRepository,
        session: AsyncSession,
    ) -> None:
        generation_id = "gen-report"
        await generation_repo.create(_generation(generation_id))

        report = _report(generation_id)
        locator = await report_repo.save_report(report)
        loaded = await report_repo.load_report(generation_id)
        stored = await generation_repo.find_by_id(generation_id)

        assert locator == f"generation:{generation_id}:report"
        assert loaded.generation_id == report.generation_id
        assert loaded.template_id == "guided-concept-path"
        assert loaded.outcome == "partial"
        assert stored is not None
        row = await session.execute(
            select(GenerationModel.report_json).where(GenerationModel.id == generation_id)
        )
        report_json = row.scalar_one()
        assert report_json is not None
        assert report_json["outcome"] == "partial"

    async def test_load_report_raises_for_missing_generation(
        self,
        report_repo: SqlGenerationReportRepository,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            await report_repo.load_report("missing-generation")
