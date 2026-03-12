import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from textbook_agent.domain.entities.generation import Generation
from textbook_agent.infrastructure.database.models import Base, UserModel
from textbook_agent.infrastructure.repositories.sql_generation_repo import (
    SqlGenerationRepository,
)

TEST_USER_ID = "test-user-001"


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        # Create a user so FK constraint is satisfied
        sess.add(
            UserModel(
                id=TEST_USER_ID,
                email="test@example.com",
                name="Test User",
            )
        )
        await sess.commit()
        yield sess

    await engine.dispose()


@pytest.fixture
def repo(session: AsyncSession) -> SqlGenerationRepository:
    return SqlGenerationRepository(session)


class TestSqlGenerationRepository:
    async def test_create_and_find(self, repo: SqlGenerationRepository):
        gen = Generation(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            subject="algebra",
            context="Help with variables",
        )
        created = await repo.create(gen)
        assert created.id == gen.id
        assert created.status == "pending"

        found = await repo.find_by_id(gen.id)
        assert found is not None
        assert found.subject == "algebra"

    async def test_update_status_completed(self, repo: SqlGenerationRepository):
        gen_id = str(uuid.uuid4())
        await repo.create(
            Generation(
                id=gen_id, user_id=TEST_USER_ID, subject="calculus", context="Integrals"
            )
        )
        await repo.update_status(
            gen_id,
            status="completed",
            output_path="/outputs/test.html",
            quality_passed=True,
            generation_time_seconds=30.5,
        )
        found = await repo.find_by_id(gen_id)
        assert found.status == "completed"
        assert found.output_path == "/outputs/test.html"
        assert found.quality_passed is True
        assert found.generation_time_seconds == 30.5
        assert found.completed_at is not None

    async def test_update_status_failed(self, repo: SqlGenerationRepository):
        gen_id = str(uuid.uuid4())
        await repo.create(
            Generation(id=gen_id, user_id=TEST_USER_ID, subject="physics")
        )
        await repo.update_status(gen_id, status="failed", error="Provider timeout")
        found = await repo.find_by_id(gen_id)
        assert found.status == "failed"
        assert found.error == "Provider timeout"
        assert found.completed_at is not None

    async def test_list_by_user_ordered_by_newest(self, repo: SqlGenerationRepository):
        for i in range(3):
            await repo.create(
                Generation(
                    id=f"gen-{i}",
                    user_id=TEST_USER_ID,
                    subject=f"subject-{i}",
                )
            )

        results = await repo.list_by_user(TEST_USER_ID)
        assert len(results) == 3
        # Most recent first
        assert results[0].id == "gen-2"
        assert results[2].id == "gen-0"

    async def test_list_by_user_with_limit(self, repo: SqlGenerationRepository):
        for i in range(5):
            await repo.create(
                Generation(
                    id=f"gen-{i}",
                    user_id=TEST_USER_ID,
                    subject=f"subject-{i}",
                )
            )

        results = await repo.list_by_user(TEST_USER_ID, limit=2)
        assert len(results) == 2

    async def test_find_nonexistent_returns_none(self, repo: SqlGenerationRepository):
        result = await repo.find_by_id("nonexistent-id")
        assert result is None
