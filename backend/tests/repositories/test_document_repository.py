from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database.models import UserModel
from generation.entities.generation import Generation
from generation.repositories.sql_document_repo import SqlDocumentRepository
from generation.repositories.sql_generation_repo import SqlGenerationRepository
from pipeline.api import PipelineDocument
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
def document_repo(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> SqlDocumentRepository:
    return SqlDocumentRepository(db_session_factory)


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
        status="running",
        section_manifest=[
            {
                "section_id": "s-01",
                "title": "Limits in Motion",
                "position": 1,
            }
        ],
        sections=[_section()],
        created_at=now,
        updated_at=now,
    )


class TestSqlDocumentRepository:
    async def test_save_and_load_document_round_trip(
        self,
        generation_repo: SqlGenerationRepository,
        document_repo: SqlDocumentRepository,
    ) -> None:
        generation_id = "gen-doc"
        await generation_repo.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER_ID,
                subject="Calculus",
                context="Explain limits",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )

        document = _document(generation_id)
        locator = await document_repo.save_document(document)
        found_generation = await generation_repo.find_by_id(generation_id)
        loaded = await document_repo.load_document(locator)

        assert locator == generation_id
        assert found_generation is not None
        assert found_generation.document_path is None
        assert loaded.generation_id == document.generation_id
        assert loaded.sections[0].section_id == "s-01"
        assert loaded.template_id == "guided-concept-path"
        assert loaded.section_manifest[0].title == "Limits in Motion"

    async def test_load_document_accepts_legacy_locator(
        self,
        generation_repo: SqlGenerationRepository,
        document_repo: SqlDocumentRepository,
    ) -> None:
        generation_id = "gen-doc-legacy"
        await generation_repo.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER_ID,
                subject="Calculus",
                context="Explain limits",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )

        document = _document(generation_id)
        await document_repo.save_document(document)
        loaded = await document_repo.load_document(f"generation:{generation_id}:document")

        assert loaded.generation_id == generation_id

    async def test_load_document_raises_for_missing_locator(
        self,
        document_repo: SqlDocumentRepository,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            await document_repo.load_document("generation:missing:document")

    async def test_save_document_supports_concurrent_calls_on_one_repository(
        self,
        generation_repo: SqlGenerationRepository,
        document_repo: SqlDocumentRepository,
    ) -> None:
        generation_id = "gen-doc-concurrent"
        await generation_repo.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER_ID,
                subject="Calculus",
                context="Explain limits",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )

        document = _document(generation_id)
        locators = await asyncio.gather(
            document_repo.save_document(document),
            document_repo.save_document(document),
        )
        loaded = await document_repo.load_document(generation_id)

        assert locators == [generation_id, generation_id]
        assert loaded.generation_id == generation_id
        assert loaded.sections[0].section_id == "s-01"
