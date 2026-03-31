import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import UserModel
from generation.entities.generation import Generation
from generation.repositories.sql_generation_repo import SqlGenerationRepository

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
def repo(session: AsyncSession) -> SqlGenerationRepository:
    return SqlGenerationRepository(session)


class TestSqlGenerationRepository:
    async def test_create_and_find(self, repo: SqlGenerationRepository):
        gen = Generation(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            subject="algebra",
            context="Help with variables",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
        )
        created = await repo.create(gen)
        assert created.id == gen.id
        assert created.status == "pending"

        found = await repo.find_by_id(gen.id)
        assert found is not None
        assert found.subject == "algebra"
        assert found.error_type is None
        assert found.error_code is None
        assert found.created_at.tzinfo is not None

    async def test_create_persists_core_generation_fields(self, repo: SqlGenerationRepository):
        gen = Generation(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            subject="algebra",
            context="Enhance this draft",
            section_count=6,
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
        )

        await repo.create(gen)
        found = await repo.find_by_id(gen.id)

        assert found is not None
        assert found.section_count == 6

    async def test_update_status_completed(self, repo: SqlGenerationRepository):
        gen_id = str(uuid.uuid4())
        await repo.create(
            Generation(
                id=gen_id,
                user_id=TEST_USER_ID,
                subject="calculus",
                context="Integrals",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )
        await repo.update_status(
            gen_id,
            status="completed",
            document_path="/outputs/documents/test.json",
            quality_passed=True,
            generation_time_seconds=30.5,
        )
        found = await repo.find_by_id(gen_id)
        assert found.status == "completed"
        assert found.document_path == "/outputs/documents/test.json"
        assert found.quality_passed is True
        assert found.generation_time_seconds == 30.5
        assert found.completed_at is not None

    async def test_update_status_failed(self, repo: SqlGenerationRepository):
        gen_id = str(uuid.uuid4())
        await repo.create(
            Generation(
                id=gen_id,
                user_id=TEST_USER_ID,
                subject="physics",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )
        await repo.update_status(
            gen_id,
            status="failed",
            error="Provider timeout",
            error_type="provider_error",
            error_code="provider_request_failed",
        )
        found = await repo.find_by_id(gen_id)
        assert found.status == "failed"
        assert found.error == "Provider timeout"
        assert found.error_type == "provider_error"
        assert found.error_code == "provider_request_failed"
        assert found.completed_at is not None

    async def test_template_metadata_round_trips(self, repo: SqlGenerationRepository):
        gen = Generation(
            id=str(uuid.uuid4()),
            user_id=TEST_USER_ID,
            subject="chemistry",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
        )

        await repo.create(gen)
        await repo.update_status(
            gen.id,
            status="completed",
            resolved_template_id="figure-first",
            resolved_preset_id="warm-paper",
        )
        found = await repo.find_by_id(gen.id)

        assert found is not None
        assert found.requested_template_id == "guided-concept-path"
        assert found.resolved_template_id == "figure-first"
        assert found.resolved_preset_id == "warm-paper"

    async def test_list_by_user_ordered_by_newest(self, repo: SqlGenerationRepository):
        for i in range(3):
            await repo.create(
                Generation(
                    id=f"gen-{i}",
                    user_id=TEST_USER_ID,
                    subject=f"subject-{i}",
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
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
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
                )
            )

        results = await repo.list_by_user(TEST_USER_ID, limit=2)
        assert len(results) == 2

    async def test_find_nonexistent_returns_none(self, repo: SqlGenerationRepository):
        result = await repo.find_by_id("nonexistent-id")
        assert result is None

    async def test_count_active_by_user_counts_pending_and_running(
        self,
        repo: SqlGenerationRepository,
    ):
        active_ids = []
        for status in ("pending", "running", "completed"):
            generation_id = str(uuid.uuid4())
            await repo.create(
                Generation(
                    id=generation_id,
                    user_id=TEST_USER_ID,
                    subject=f"subject-{status}",
                    context="",
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
                )
            )
            await repo.update_status(generation_id, status=status)
            active_ids.append(generation_id)

        count = await repo.count_active_by_user(TEST_USER_ID)

        assert count == 2

    async def test_update_heartbeat_sets_last_heartbeat(self, repo: SqlGenerationRepository):
        generation_id = str(uuid.uuid4())
        await repo.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER_ID,
                subject="geometry",
                context="",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )

        heartbeat_at = datetime(2026, 3, 28, 22, 30, tzinfo=timezone.utc)
        await repo.update_heartbeat(generation_id, heartbeat_at=heartbeat_at)

        found = await repo.find_by_id(generation_id)
        assert found is not None
        assert found.last_heartbeat == heartbeat_at

