import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import GenerationModel
from core.database.session import get_async_session
from pipeline.api import PipelineDocument, PipelineResult
from pipeline.events import SectionReadyEvent, SectionStartedEvent
from pipeline.types.requests import SectionPlan
from planning.dtos import BriefRequest, GenerationSpec
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
from generation.entities.generation import Generation
from core.entities.student_profile import StudentProfile
from core.entities.user import User
from app import app, create_app
from generation.recovery import (
    INTERRUPTED_GENERATION_ERROR_CODE,
    WORKER_RESTART_GENERATION_ERROR_CODE,
    mark_stale_generations_failed,
)
from core.dependencies import get_jwt_handler
from generation.dependencies import get_document_repository, get_generation_repository
from core.dependencies import get_student_profile_repository, get_user_repository
from core.auth.middleware import get_current_user
from generation import routes as generation_routes
from telemetry.dependencies import get_report_repository
from telemetry.dtos import GenerationReport


def _now() -> datetime:
    return datetime.now(timezone.utc)


TEST_USER = User(
    id="test-user-id",
    email="test@example.com",
    name="Test User",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
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
            body="A limit studies nearby behavior. We watch what happens as x gets closer and closer to a chosen point.",
            emphasis=["nearby behavior", "approach", "pattern"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="Describe what f(x) does near x = 2.",
                    hints=[PracticeHint(level=1, text="Look at values close to 2.")],
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


def _document(
    generation_id: str,
    *,
    mode: str = "balanced",
    status: str = "completed",
    sections: list[SectionContent] | None = None,
) -> PipelineDocument:
    return PipelineDocument(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        mode=mode,
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status=status,
        section_manifest=[
            {
                "section_id": section.section_id,
                "title": section.header.title,
                "position": index + 1,
            }
            for index, section in enumerate(sections or [_section()])
        ],
        sections=sections or [_section()],
        failed_sections=[],
        qc_reports=[],
        quality_passed=True if status == "completed" else None,
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now() if status == "completed" else None,
    )


def _generation_spec() -> GenerationSpec:
    return GenerationSpec(
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        mode="balanced",
        section_count=3,
        sections=[
            SectionPlan(
                section_id="section-1",
                position=1,
                title="Limits first look",
                focus="Introduce the core idea of approaching a value.",
                role="intro",
            ),
            SectionPlan(
                section_id="section-2",
                position=2,
                title="Work a limit",
                focus="Show a concrete worked example.",
                role="develop",
                needs_worked_example=True,
                required_components=["worked_example"],
            ),
            SectionPlan(
                section_id="section-3",
                position=3,
                title="Check understanding",
                focus="End with practice and a short summary bridge.",
                role="practice",
                required_components=["practice", "what_next"],
            ),
        ],
        warning=None,
        rationale="Guided concept path suits a compact calculus lesson.",
        source_brief=BriefRequest(
            intent="Teach limits",
            audience="High school calculus students",
            extra_context="Keep it concise.",
        ),
    )


class InMemoryGenerationRepo:
    def __init__(self) -> None:
        self.store: dict[str, Generation] = {}

    async def create(self, generation: Generation) -> Generation:
        self.store[generation.id] = generation
        return generation

    async def update_status(self, generation_id: str, status: str, **kwargs) -> None:
        generation = self.store[generation_id]
        updates = {"status": status}
        updates.update({key: value for key, value in kwargs.items() if value is not None})
        if status in {"completed", "failed"}:
            updates["completed_at"] = _now()
        self.store[generation_id] = generation.model_copy(update=updates)

    async def find_by_id(self, generation_id: str) -> Generation | None:
        return self.store.get(generation_id)

    async def list_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> list[Generation]:
        items = [generation for generation in self.store.values() if generation.user_id == user_id]
        items.sort(key=lambda generation: generation.created_at, reverse=True)
        return items[offset : offset + limit]

    async def count_active_by_user(self, user_id: str) -> int:
        return sum(
            1
            for generation in self.store.values()
            if generation.user_id == user_id and generation.status in {"pending", "running"}
        )

    async def update_heartbeat(self, generation_id: str, heartbeat_at: datetime | None = None) -> None:
        generation = self.store[generation_id]
        self.store[generation_id] = generation.model_copy(
            update={"last_heartbeat": heartbeat_at or _now()}
        )


class InMemoryDocumentRepo:
    def __init__(self) -> None:
        self.store: dict[str, PipelineDocument] = {}

    async def save_document(self, document: PipelineDocument) -> str:
        path = f"memory://{document.generation_id}"
        self.store[path] = document
        return path

    async def load_document(self, path: str) -> PipelineDocument:
        return self.store[path]


class InMemoryReportRepo:
    def __init__(self) -> None:
        self.store: dict[str, GenerationReport] = {}

    async def save_report(self, report: GenerationReport) -> str:
        self.store[report.generation_id] = report
        return f"memory://report/{report.generation_id}"

    async def load_report(self, generation_id: str) -> GenerationReport:
        return self.store[generation_id]

    async def cleanup_tmp(self, generation_id: str) -> None:
        _ = generation_id


class FailingOnCallReportRepo(InMemoryReportRepo):
    def __init__(self, *, fail_on_calls: set[int]) -> None:
        super().__init__()
        self.fail_on_calls = set(fail_on_calls)
        self.save_calls = 0

    async def save_report(self, report: GenerationReport) -> str:
        self.save_calls += 1
        if self.save_calls in self.fail_on_calls:
            raise RuntimeError(f"report persistence failed on call {self.save_calls}")
        return await super().save_report(report)


class StaticProfileRepo:
    def __init__(self, profile: StudentProfile | None) -> None:
        self.profile = profile

    async def find_by_user_id(self, user_id: str) -> StudentProfile | None:
        _ = user_id
        return self.profile

    async def create(self, profile: StudentProfile) -> StudentProfile:
        self.profile = profile
        return profile

    async def update(self, profile: StudentProfile) -> StudentProfile:
        self.profile = profile
        return profile


class StaticUserRepo:
    async def find_by_email(self, email: str) -> User | None:
        return TEST_USER if email == TEST_USER.email else None

    async def find_by_id(self, user_id: str) -> User | None:
        return TEST_USER if user_id == TEST_USER.id else None

    async def create(self, user: User) -> User:
        return user

    async def update(self, user: User) -> User:
        return user


PROFILE = StudentProfile(
    id="profile-id",
    user_id=TEST_USER.id,
    age=16,
    education_level="high_school",
    interests=["math"],
    learning_style="visual",
    preferred_notation="plain",
    prior_knowledge="basic algebra",
    goals="understand limits",
    preferred_depth="standard",
    learner_description="Curious and steady",
    created_at=_now(),
    updated_at=_now(),
)

GEN_REPO = InMemoryGenerationRepo()
DOC_REPO = InMemoryDocumentRepo()
REPORT_REPO = InMemoryReportRepo()
USER_REPO = StaticUserRepo()
PROFILE_REPO = StaticProfileRepo(PROFILE)


async def override_current_user():
    return TEST_USER


async def override_generation_repo():
    return GEN_REPO


async def override_document_repo():
    return DOC_REPO


async def override_profile_repo():
    return PROFILE_REPO


async def override_user_repo():
    return USER_REPO


async def override_report_repo():
    return REPORT_REPO


app.dependency_overrides[get_current_user] = override_current_user
app.dependency_overrides[get_generation_repository] = override_generation_repo
app.dependency_overrides[get_document_repository] = override_document_repo
app.dependency_overrides[get_student_profile_repository] = override_profile_repo
app.dependency_overrides[get_user_repository] = override_user_repo
app.dependency_overrides[get_report_repository] = override_report_repo


@pytest.fixture(autouse=True)
def _install_dependency_overrides():
    GEN_REPO.store.clear()
    DOC_REPO.store.clear()
    REPORT_REPO.store.clear()
    PROFILE_REPO.profile = PROFILE
    app.dependency_overrides.clear()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_user_repository] = override_user_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    yield
    GEN_REPO.store.clear()
    DOC_REPO.store.clear()
    REPORT_REPO.store.clear()
    app.dependency_overrides.clear()

JWT_HANDLER = get_jwt_handler()
AUTH_HEADERS = {
    "Authorization": f"Bearer {JWT_HANDLER.create_access_token(TEST_USER.id, TEST_USER.email)}"
}


async def _seed_generation_row(
    session: AsyncSession,
    *,
    generation_id: str,
    user_id: str,
) -> None:
    await session.execute(delete(GenerationModel).where(GenerationModel.id == generation_id))
    session.add(
        GenerationModel(
            id=generation_id,
            user_id=user_id,
            subject="Calculus",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            status="completed",
        )
    )
    await session.commit()


@asynccontextmanager
async def _client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


class TestHealthAndAuth:
    async def test_health_returns_pipeline_runtime_metadata(self):
        with TestClient(create_app()) as client:
            response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["pipeline_architecture"] == "shell-pipeline-native-lectio"

    async def test_health_includes_security_headers(self):
        with TestClient(create_app()) as client:
            response = client.get("/health")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    async def test_readiness_returns_ok_when_database_and_key_are_available(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        with TestClient(create_app()) as client:
            response = client.get("/health/ready")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["checks"]["database"] == "ok"
        assert payload["checks"]["anthropic_api_key"] == "present"

    async def test_readiness_returns_degraded_when_database_check_fails(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        app = create_app()

        class BrokenSession:
            async def execute(self, *_args, **_kwargs):
                raise RuntimeError("db offline")

        async def override_session():
            yield BrokenSession()

        app.dependency_overrides[get_async_session] = override_session
        try:
            with TestClient(app) as client:
                response = client.get("/health/ready")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 503
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["checks"]["database"].startswith("failed:")

    async def test_auth_me_returns_current_user(self):
        async with _client() as client:
            response = await client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
        assert response.status_code == 200
        assert response.json()["id"] == TEST_USER.id


class TestGenerationApi:
    async def test_create_generation_accepts_valid_template_and_preset(self):
        async def fake_run_pipeline(command, on_event=None):
            return PipelineResult(
                document=_document(command.generation_id or "gen-test"),
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=0.01,
            )

        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 4,
                    },
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        assert response.status_code == 202
        payload = response.json()
        assert "mode" not in payload
        assert payload["events_url"].endswith("/events")

    async def test_create_generation_uses_generation_spec_as_source_of_truth(self):
        captured: dict[str, object] = {}
        spec = _generation_spec()

        async def fake_run_pipeline(command, on_event=None):
            captured["command"] = command
            return PipelineResult(
                document=_document(command.generation_id or "gen-spec", mode="balanced"),
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=0.01,
            )

        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Teach limits",
                        "context": "legacy context should be ignored",
                        "template_id": "timeline-narrative",
                        "preset_id": "blue-classroom",
                        "section_count": 1,
                        "generation_spec": spec.model_dump(mode="json"),
                    },
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        assert response.status_code == 202
        command = captured["command"]
        assert command.template_id == spec.template_id
        assert command.section_count == spec.section_count
        assert command.section_plans is not None
        assert len(command.section_plans) == 3
        assert "Reviewed lesson plan:" in command.context
        accepted = response.json()
        assert accepted["report_url"].endswith("/report")
        stored = await GEN_REPO.find_by_id(accepted["generation_id"])
        assert stored is not None
        assert stored.planning_spec_json is not None
        assert stored.requested_template_id == "guided-concept-path"
        assert stored.requested_preset_id == "blue-classroom"
        assert stored.section_count == 3

    async def test_create_generation_rejects_invalid_template_pair(self):
        async with _client() as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "subject": "Calculus",
                    "context": "Explain limits",
                    "template_id": "guided-concept-path",
                    "preset_id": "minimal-light",
                    "section_count": 4,
                },
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    async def test_create_generation_rejects_when_user_has_too_many_active_generations(self):
        for index in range(2):
            await GEN_REPO.create(
                Generation(
                    id=f"gen-active-{index}",
                    user_id=TEST_USER.id,
                    subject=f"Active {index}",
                    context="Still running",
                    status="running",
                    requested_template_id="guided-concept-path",
                    requested_preset_id="blue-classroom",
                    last_heartbeat=_now(),
                )
            )

        async with _client() as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "subject": "Calculus",
                    "context": "Explain limits",
                    "template_id": "guided-concept-path",
                    "preset_id": "blue-classroom",
                    "section_count": 4,
                },
                headers=AUTH_HEADERS,
            )

        assert response.status_code == 429
        assert "Maximum 2 concurrent generations allowed" in response.json()["detail"]

    async def test_create_generation_rejects_blank_trimmed_fields(self):
        async with _client() as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "subject": "   ",
                    "context": "Explain limits",
                    "template_id": "guided-concept-path",
                    "preset_id": "blue-classroom",
                    "section_count": 4,
                },
                headers=AUTH_HEADERS,
            )

        assert response.status_code == 422

    async def test_create_generation_rejects_section_count_above_phase_six_cap(self):
        async with _client() as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "subject": "Calculus",
                    "context": "Explain limits",
                    "template_id": "guided-concept-path",
                    "preset_id": "blue-classroom",
                    "section_count": 9,
                },
                headers=AUTH_HEADERS,
            )

        assert response.status_code == 422

    async def test_document_endpoint_returns_saved_json_document(self):
        generation_id = "gen-doc"
        document = _document(generation_id)
        path = await DOC_REPO.save_document(document)
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="completed",
                document_path=path,
                requested_template_id="guided-concept-path",
                resolved_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                resolved_preset_id="blue-classroom",
                quality_passed=True,
            )
        )

        async with _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/document",
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["template_id"] == "guided-concept-path"
        assert payload["section_manifest"][0]["section_id"] == "s-01"
        assert payload["sections"][0]["section_id"] == "s-01"

    async def test_generation_detail_and_history_include_section_count(self):
        generation_id = "gen-history"
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="completed",
                document_path="memory://gen-history",
                requested_template_id="guided-concept-path",
                resolved_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                resolved_preset_id="blue-classroom",
                section_count=5,
                quality_passed=True,
            )
        )

        async with _client() as client:
            detail_response = await client.get(
                f"/api/v1/generations/{generation_id}",
                headers=AUTH_HEADERS,
            )
            history_response = await client.get(
                "/api/v1/generations",
                headers=AUTH_HEADERS,
            )

        assert detail_response.status_code == 200
        assert detail_response.json()["section_count"] == 5
        assert detail_response.json()["report_url"].endswith("/report")
        assert any(item["section_count"] == 5 for item in history_response.json())

    async def test_generation_report_endpoint_returns_saved_report(self, db_session: AsyncSession):
        generation_id = "gen-report"
        await REPORT_REPO.save_report(
            GenerationReport(
                generation_id=generation_id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                template_id="guided-concept-path",
                preset_id="blue-classroom",
                status="completed",
                outcome="partial",
                section_count=2,
            )
        )
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="completed",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )
        await _seed_generation_row(
            db_session,
            generation_id=generation_id,
            user_id=TEST_USER.id,
        )

        async def override_async_session():
            yield db_session

        app.dependency_overrides[get_async_session] = override_async_session

        async with _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/report",
                headers=AUTH_HEADERS,
            )

        app.dependency_overrides.pop(get_async_session, None)

        assert response.status_code == 200
        payload = response.json()
        assert payload["generation_id"] == generation_id
        assert payload["outcome"] == "partial"

    async def test_generation_report_endpoint_requires_ownership(self, db_session: AsyncSession):
        generation_id = "gen-report-hidden"
        await REPORT_REPO.save_report(
            GenerationReport(
                generation_id=generation_id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                template_id="guided-concept-path",
                preset_id="blue-classroom",
                status="completed",
            )
        )
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id="someone-else",
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="completed",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
            )
        )
        await _seed_generation_row(
            db_session,
            generation_id=generation_id,
            user_id="different-user-id",
        )

        async def override_async_session():
            yield db_session

        app.dependency_overrides[get_async_session] = override_async_session

        async with _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/report",
                headers=AUTH_HEADERS,
            )

        app.dependency_overrides.pop(get_async_session, None)

        assert response.status_code == 404

    async def test_events_endpoint_supports_stream_token_for_completed_generation(self):
        generation_id = "gen-events"
        document = _document(generation_id)
        path = await DOC_REPO.save_document(document)
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="completed",
                document_path=path,
                requested_template_id="guided-concept-path",
                resolved_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                resolved_preset_id="blue-classroom",
                quality_passed=True,
            )
        )

        token = JWT_HANDLER.create_access_token(TEST_USER.id, TEST_USER.email)
        async with _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/events?token={token}",
            )
        assert response.status_code == 200
        assert "event: complete" in response.text
        assert "event: progress_update" in response.text
        assert "/report" in response.text

    async def test_events_endpoint_returns_terminal_error_for_failed_generation(self):
        generation_id = "gen-failed-events"
        document = _document(generation_id, status="failed").model_copy(
            update={
                "quality_passed": False,
                "error": "Generation was interrupted before it finished. Please try again.",
                "completed_at": _now(),
            }
        )
        path = await DOC_REPO.save_document(document)
        await GEN_REPO.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="failed",
                document_path=path,
                error=document.error,
                error_type="runtime_error",
                error_code=INTERRUPTED_GENERATION_ERROR_CODE,
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                quality_passed=False,
            )
        )

        token = JWT_HANDLER.create_access_token(TEST_USER.id, TEST_USER.email)
        async with _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/events?token={token}",
            )

        assert response.status_code == 200
        assert "event: error" in response.text
        assert "event: progress_update" in response.text
        assert "interrupted before it finished" in response.text

    async def test_streaming_partial_saves_keep_manifest_and_section_order(self):
        async def fake_run_pipeline(command, on_event=None):
            await on_event(
                SectionStartedEvent(
                    generation_id=command.generation_id or "gen-partial",
                    section_id="s-01",
                    title="First section",
                    position=1,
                )
            )
            await on_event(
                SectionStartedEvent(
                    generation_id=command.generation_id or "gen-partial",
                    section_id="s-02",
                    title="Second section",
                    position=2,
                )
            )
            await on_event(
                SectionReadyEvent(
                    generation_id=command.generation_id or "gen-partial",
                    section_id="s-02",
                    section=_section("s-02"),
                    completed_sections=1,
                    total_sections=2,
                )
            )
            partial_document = DOC_REPO.store[f"memory://{command.generation_id}"]
            assert [item.section_id for item in partial_document.section_manifest] == ["s-01", "s-02"]
            assert [section.section_id for section in partial_document.sections] == ["s-02"]

            await on_event(
                SectionReadyEvent(
                    generation_id=command.generation_id or "gen-partial",
                    section_id="s-01",
                    section=_section("s-01"),
                    completed_sections=2,
                    total_sections=2,
                )
            )
            ordered_document = DOC_REPO.store[f"memory://{command.generation_id}"]
            assert [section.section_id for section in ordered_document.sections] == ["s-01", "s-02"]

            return PipelineResult(
                document=_document(
                    command.generation_id or "gen-partial",
                    sections=[_section("s-01"), _section("s-02")],
                ),
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=0.01,
            )

        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 2,
                    },
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        assert response.status_code == 202

    async def test_completed_generation_with_missing_sections_writes_partial_report(self):
        async def fake_run_pipeline(command, on_event=None):
            for index, section_id in enumerate(("s-01", "s-02", "s-03", "s-04"), start=1):
                await on_event(
                    SectionStartedEvent(
                        generation_id=command.generation_id or "gen-missing",
                        section_id=section_id,
                        title=f"Section {index}",
                        position=index,
                    )
                )
            await on_event(
                SectionReadyEvent(
                    generation_id=command.generation_id or "gen-missing",
                    section_id="s-01",
                    section=_section("s-01"),
                    completed_sections=1,
                    total_sections=4,
                )
            )
            await on_event(
                SectionReadyEvent(
                    generation_id=command.generation_id or "gen-missing",
                    section_id="s-02",
                    section=_section("s-02"),
                    completed_sections=2,
                    total_sections=4,
                )
            )
            document = _document(
                command.generation_id or "gen-missing",
                sections=[_section("s-01"), _section("s-02")],
            ).model_copy(
                update={
                    "section_manifest": [
                        {"section_id": "s-01", "title": "Section 1", "position": 1},
                        {"section_id": "s-02", "title": "Section 2", "position": 2},
                        {"section_id": "s-03", "title": "Section 3", "position": 3},
                        {"section_id": "s-04", "title": "Section 4", "position": 4},
                    ]
                }
            )
            return PipelineResult(
                document=document,
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=9.5,
            )

        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 4,
                    },
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        report = await REPORT_REPO.load_report(response.json()["generation_id"])
        assert report.status == "completed"
        assert report.outcome == "partial"
        assert report.summary.ready_sections == 2
        assert {section.section_id for section in report.sections if section.status != "ready"} == {
            "s-03",
            "s-04",
        }

    async def test_enhance_generation_endpoint_is_removed(self):
        async with _client() as client:
            response = await client.post(
                "/api/v1/generations/gen-draft/enhance",
                json={"note": "Tighten the worked explanation."},
                headers=AUTH_HEADERS,
            )

        assert response.status_code == 404

    async def test_run_generation_job_marks_cancelled_task_failed_without_direct_report_writes(self):
        generation_id = "gen-cancelled"
        generation = Generation(
            id=generation_id,
            user_id=TEST_USER.id,
            subject="Calculus",
            context="Explain limits",
            mode="balanced",
            status="pending",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            section_count=1,
        )
        initial_document = _document(generation_id, status="pending").model_copy(
            update={"quality_passed": None, "completed_at": None, "error": None}
        )
        generation.document_path = await DOC_REPO.save_document(initial_document)
        await GEN_REPO.create(generation)

        command = generation_routes.PipelineCommand(
            generation_id=generation_id,
            subject="Calculus",
            context="Explain limits",
            grade_band="secondary",
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            learner_fit="general",
            section_count=1,
            mode="balanced",
        )

        async def cancelled_run_pipeline(command, on_event=None):
            _ = (command, on_event)
            raise asyncio.CancelledError

        with patch.object(
            generation_routes,
            "run_pipeline_streaming",
            create=True,
            side_effect=cancelled_run_pipeline,
        ):
            await generation_routes._run_generation_job(
                generation,
                command,
                GEN_REPO,
                DOC_REPO,
                REPORT_REPO,
                initial_document,
            )

        updated = await GEN_REPO.find_by_id(generation_id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_code == INTERRUPTED_GENERATION_ERROR_CODE
        assert updated.quality_passed is False

        document = await DOC_REPO.load_document(updated.document_path or "")
        assert document.status == "failed"
        assert document.quality_passed is False
        assert document.error is not None

        assert generation_id not in REPORT_REPO.store

    async def test_stale_generation_recovery_updates_generation_and_document_only(self):
        generation_id = "gen-stale"
        running_document = _document(generation_id, status="running").model_copy(
            update={"quality_passed": True, "completed_at": None}
        )
        path = await DOC_REPO.save_document(running_document)
        generation = Generation(
            id=generation_id,
            user_id=TEST_USER.id,
            subject="Calculus",
            context="Explain limits",
            mode="balanced",
            status="running",
            document_path=path,
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            section_count=1,
            quality_passed=True,
        )
        await GEN_REPO.create(generation)
        await REPORT_REPO.save_report(
            GenerationReport(
                generation_id=generation_id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                template_id="guided-concept-path",
                preset_id="blue-classroom",
                status="running",
                section_count=1,
                quality_passed=True,
            )
        )

        count = await mark_stale_generations_failed(
            [generation],
            generation_repository=GEN_REPO,
            document_repository=DOC_REPO,
            report_repository=REPORT_REPO,
        )

        assert count == 1
        updated = await GEN_REPO.find_by_id(generation_id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_code == WORKER_RESTART_GENERATION_ERROR_CODE
        assert updated.error_type == "worker_restart"
        assert updated.quality_passed is False

        document = await DOC_REPO.load_document(updated.document_path or "")
        assert document.status == "failed"
        assert document.quality_passed is False

        report = await REPORT_REPO.load_report(generation_id)
        assert report.status == "running"
        assert report.quality_passed is True

    async def test_run_generation_job_ignores_report_repo_after_telemetry_extraction(self):
        generation_id = "gen-complete-report-failure"
        generation = Generation(
            id=generation_id,
            user_id=TEST_USER.id,
            subject="Calculus",
            context="Explain limits",
            mode="balanced",
            status="pending",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            section_count=1,
        )
        gen_repo = InMemoryGenerationRepo()
        doc_repo = InMemoryDocumentRepo()
        report_repo = FailingOnCallReportRepo(fail_on_calls={2})
        initial_document = _document(generation_id, status="pending").model_copy(
            update={"quality_passed": None, "completed_at": None, "error": None}
        )
        generation.document_path = await doc_repo.save_document(initial_document)
        await gen_repo.create(generation)

        command = generation_routes.PipelineCommand(
            generation_id=generation_id,
            subject="Calculus",
            context="Explain limits",
            grade_band="secondary",
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            learner_fit="general",
            section_count=1,
            mode="balanced",
        )
        queue = generation_routes.event_bus.subscribe(generation_id)

        async def fake_run_pipeline(command, on_event=None):
            _ = on_event
            return PipelineResult(
                document=_document(command.generation_id or generation_id).model_copy(
                    update={"quality_passed": False}
                ),
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=0.01,
            )

        with patch.object(
            generation_routes,
            "run_pipeline_streaming",
            create=True,
            side_effect=fake_run_pipeline,
        ):
            await generation_routes._run_generation_job(
                generation,
                command,
                gen_repo,
                doc_repo,
                report_repo,
                initial_document,
            )

        try:
            events = []
            while not queue.empty():
                events.append(queue.get_nowait())
        finally:
            generation_routes.event_bus.unsubscribe(generation_id, queue)

        updated = await gen_repo.find_by_id(generation_id)
        assert updated is not None
        assert updated.status == "completed"
        assert updated.quality_passed is False
        assert any(event["type"] == "complete" for event in events)

        assert generation_id not in report_repo.store
        assert report_repo.save_calls == 0

    async def test_run_generation_job_marks_timeout_failed_without_direct_report_writes(self, monkeypatch):
        generation_id = "gen-timeout"
        generation = Generation(
            id=generation_id,
            user_id=TEST_USER.id,
            subject="Calculus",
            context="Explain limits",
            mode="balanced",
            status="pending",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            section_count=1,
        )
        gen_repo = InMemoryGenerationRepo()
        doc_repo = InMemoryDocumentRepo()
        report_repo = InMemoryReportRepo()
        initial_document = _document(generation_id, status="pending").model_copy(
            update={"quality_passed": None, "completed_at": None, "error": None}
        )
        generation.document_path = await doc_repo.save_document(initial_document)
        await gen_repo.create(generation)

        command = generation_routes.PipelineCommand(
            generation_id=generation_id,
            subject="Calculus",
            context="Explain limits",
            grade_band="secondary",
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            learner_fit="general",
            section_count=1,
            mode="balanced",
        )

        async def slow_run_pipeline(command, on_event=None):
            _ = (command, on_event)
            await asyncio.sleep(0.05)
            return PipelineResult(
                document=_document(generation_id),
                completed_nodes=["curriculum_planner"],
                generation_time_seconds=0.05,
            )

        monkeypatch.setattr(generation_routes, "_generation_job_timeout", lambda n: 0.01)
        with patch.object(
            generation_routes,
            "run_pipeline_streaming",
            create=True,
            side_effect=slow_run_pipeline,
        ):
            await generation_routes._run_generation_job(
                generation,
                command,
                gen_repo,
                doc_repo,
                report_repo,
                initial_document,
            )

        updated = await gen_repo.find_by_id(generation_id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_code == "generation_timeout"

        assert generation_id not in report_repo.store

    async def test_run_generation_job_forces_orphan_failure_when_primary_persist_breaks_without_direct_report_writes(self):
        generation_id = "gen-orphaned"
        generation = Generation(
            id=generation_id,
            user_id=TEST_USER.id,
            subject="Calculus",
            context="Explain limits",
            mode="balanced",
            status="pending",
            requested_template_id="guided-concept-path",
            requested_preset_id="blue-classroom",
            section_count=1,
        )
        gen_repo = InMemoryGenerationRepo()
        doc_repo = InMemoryDocumentRepo()
        report_repo = InMemoryReportRepo()
        initial_document = _document(generation_id, status="pending").model_copy(
            update={"quality_passed": None, "completed_at": None, "error": None}
        )
        generation.document_path = await doc_repo.save_document(initial_document)
        await gen_repo.create(generation)

        command = generation_routes.PipelineCommand(
            generation_id=generation_id,
            subject="Calculus",
            context="Explain limits",
            grade_band="secondary",
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            learner_fit="general",
            section_count=1,
            mode="balanced",
        )

        async def broken_run_pipeline(command, on_event=None):
            _ = (command, on_event)
            raise RuntimeError("pipeline blew up")

        original_persist_failure = generation_routes._persist_failed_generation_state
        call_count = 0

        async def flaky_persist_failure(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("failed to persist primary failure")
            return await original_persist_failure(**kwargs)

        with patch.object(
            generation_routes,
            "run_pipeline_streaming",
            create=True,
            side_effect=broken_run_pipeline,
        ), patch.object(
            generation_routes,
            "_persist_failed_generation_state",
            side_effect=flaky_persist_failure,
        ):
            await generation_routes._run_generation_job(
                generation,
                command,
                gen_repo,
                doc_repo,
                report_repo,
                initial_document,
            )

        updated = await gen_repo.find_by_id(generation_id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error_code == "orphaned_generation"

        assert generation_id not in report_repo.store

    async def test_events_endpoint_self_heals_from_terminal_db_state_after_keep_alive_timeout(
        self,
    ):
        class FlippingGenerationRepo(InMemoryGenerationRepo):
            def __init__(self) -> None:
                super().__init__()
                self.find_calls = 0

            async def find_by_id(self, generation_id: str) -> Generation | None:
                self.find_calls += 1
                generation = await super().find_by_id(generation_id)
                if generation is None:
                    return None
                if self.find_calls >= 3:
                    return generation.model_copy(update={"status": "completed"})
                return generation

        generation_id = "gen-sse-heal"
        generation_repo = FlippingGenerationRepo()
        document_repo = InMemoryDocumentRepo()
        report_repo = InMemoryReportRepo()
        profile_repo = StaticProfileRepo(PROFILE)
        user_repo = StaticUserRepo()
        app = create_app()

        document = _document(generation_id, status="running").model_copy(
            update={"quality_passed": None, "completed_at": None}
        )
        path = await document_repo.save_document(document)
        await generation_repo.create(
            Generation(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="balanced",
                status="running",
                document_path=path,
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                quality_passed=None,
            )
        )

        async def override_current_user():
            return TEST_USER

        async def override_generation_repo():
            return generation_repo

        async def override_document_repo():
            return document_repo

        async def override_profile_repo():
            return profile_repo

        async def override_user_repo():
            return user_repo

        async def override_report_repo():
            return report_repo

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_generation_repository] = override_generation_repo
        app.dependency_overrides[get_document_repository] = override_document_repo
        app.dependency_overrides[get_student_profile_repository] = override_profile_repo
        app.dependency_overrides[get_user_repository] = override_user_repo
        app.dependency_overrides[get_report_repository] = override_report_repo

        original_wait_for = generation_routes.asyncio.wait_for

        async def immediate_timeout(awaitable, timeout):
            if timeout == generation_routes._SSE_KEEPALIVE_TIMEOUT_SECONDS:
                awaitable.close()
                raise TimeoutError
            return await original_wait_for(awaitable, timeout)

        token = JWT_HANDLER.create_access_token(TEST_USER.id, TEST_USER.email)
        try:
            with patch.object(
                generation_routes.asyncio,
                "wait_for",
                side_effect=immediate_timeout,
            ):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(
                        f"/api/v1/generations/{generation_id}/events?token={token}",
                    )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert "event: complete" in response.text

