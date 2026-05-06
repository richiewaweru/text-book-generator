from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import create_app
from core.auth.middleware import get_current_user
from core.database.models import GenerationModel, UserModel
from core.database.session import get_async_session
from core.entities.user import User
from generation.dependencies import get_document_repository, get_generation_repository
from generation.entities.generation import Generation
from generation.repositories.sql_document_repo import SqlDocumentRepository
from generation.repositories.sql_generation_repo import SqlGenerationRepository
from pipeline.api import PipelineDocument
from telemetry.dependencies import get_report_repository
from telemetry.dtos import GenerationReport, GenerationReportSummary
from telemetry.repositories.sql_generation_report_repo import (
    SqlGenerationReportRepository,
)
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    WhatNextContent,
)


TEST_USER = User(
    id="route-user-id",
    email="route@example.com",
    name="Route User",
    picture_url=None,
    has_profile=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)


def _section(section_id: str = "s-01") -> SectionContent:
    return SectionContent(
        section_id=section_id,
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title="Limits in Motion",
            subject="Calculus",
            grade_band="secondary",
        ),
        hook=HookHeroContent(
            headline="Why a moving graph still tells a stable story",
            body="Limits let us describe what a function is approaching without requiring the final value yet.",
            anchor="limits",
        ),
        explanation=ExplanationContent(
            body="A limit studies nearby behavior.",
            emphasis=["nearby behavior"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="Describe what f(x) does near x = 2.",
                    hints=[PracticeHint(level=1, text="Look close to 2.")],
                ),
                PracticeProblem(
                    difficulty="medium",
                    question="Estimate lim x->2 of x^2.",
                    hints=[PracticeHint(level=1, text="Square numbers near 2.")],
                ),
            ]
        ),
        what_next=WhatNextContent(
            body="Next we connect limits to continuity.",
            next="Continuity",
        ),
    )


def _document(generation_id: str = "gen-doc") -> PipelineDocument:
    now = datetime.now(timezone.utc)
    return PipelineDocument(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="completed",
        section_manifest=[
            {
                "section_id": "s-01",
                "title": "Limits in Motion",
                "position": 1,
            }
        ],
        sections=[_section()],
        quality_passed=True,
        created_at=now,
        updated_at=now,
        completed_at=now,
    )


def _report(generation_id: str = "gen-report") -> GenerationReport:
    now = datetime.now(timezone.utc)
    return GenerationReport(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="completed",
        outcome="partial",
        section_count=1,
        quality_passed=True,
        started_at=now,
        completed_at=now,
        summary=GenerationReportSummary(planned_sections=1, ready_sections=1),
    )


@pytest.fixture
async def session(db_session: AsyncSession):
    db_session.add(
        UserModel(
            id=TEST_USER.id,
            email=TEST_USER.email,
            name=TEST_USER.name,
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
def document_repo(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> SqlDocumentRepository:
    return SqlDocumentRepository(db_session_factory)


@pytest.fixture
def report_repo(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> SqlGenerationReportRepository:
    return SqlGenerationReportRepository(db_session_factory)


@pytest.mark.asyncio
async def test_document_and_report_routes_load_json_backed_persistence(
    generation_repo: SqlGenerationRepository,
    document_repo: SqlDocumentRepository,
    report_repo: SqlGenerationReportRepository,
    db_session: AsyncSession,
) -> None:
    generation_id = "gen-route"
    generation = Generation(
        id=generation_id,
        user_id=TEST_USER.id,
        subject="Calculus",
        context="Explain limits",
        requested_template_id="guided-concept-path",
        requested_preset_id="blue-classroom",
        section_count=1,
    )
    await generation_repo.create(generation)
    generation.document_path = await document_repo.save_document(_document(generation_id))
    await report_repo.save_report(_report(generation_id))

    app = create_app()

    async def override_current_user() -> User:
        return TEST_USER

    async def override_generation_repo():
        return generation_repo

    async def override_document_repo():
        return document_repo

    async def override_report_repo():
        return report_repo

    async def override_async_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[get_async_session] = override_async_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            document_response = await client.get(f"/api/v1/generations/{generation_id}/document")
            report_response = await client.get(f"/api/v1/generations/{generation_id}/report")
    finally:
        app.dependency_overrides.clear()

    assert document_response.status_code == 200
    assert document_response.json()["generation_id"] == generation_id
    assert document_response.json()["sections"][0]["section_id"] == "s-01"
    assert report_response.status_code == 200
    assert report_response.json()["generation_id"] == generation_id
    assert report_response.json()["outcome"] == "partial"


@pytest.mark.asyncio
async def test_document_route_prefers_v3_document_json_when_present(
    generation_repo: SqlGenerationRepository,
    document_repo: SqlDocumentRepository,
    db_session: AsyncSession,
) -> None:
    generation_id = "gen-route-v3"
    generation = Generation(
        id=generation_id,
        user_id=TEST_USER.id,
        subject="Science",
        context="Cells",
        mode="balanced",
        requested_template_id="guided-concept-path",
        requested_preset_id="v3-studio",
        section_count=1,
    )
    await generation_repo.create(generation)
    generation.document_path = await document_repo.save_document(_document(generation_id))

    model = await db_session.get(GenerationModel, generation_id)
    assert model is not None
    model.document_json = {
        "kind": "v3_booklet_pack",
        "generation_id": generation_id,
        "template_id": "guided-concept-path",
        "status": "final_ready",
        "sections": [{"section_id": "s-v3", "header": {"title": "V3 Intro"}}],
    }
    await db_session.commit()

    app = create_app()

    async def override_current_user() -> User:
        return TEST_USER

    async def override_generation_repo():
        return generation_repo

    async def override_document_repo():
        return document_repo

    async def override_async_session():
        yield db_session

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_async_session] = override_async_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            document_response = await client.get(f"/api/v1/generations/{generation_id}/document")
    finally:
        app.dependency_overrides.clear()

    assert document_response.status_code == 200
    payload = document_response.json()
    assert payload["kind"] == "v3_booklet_pack"
    assert payload["sections"][0]["section_id"] == "s-v3"
