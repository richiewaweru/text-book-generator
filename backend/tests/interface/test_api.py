import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from pipeline.api import PipelineDocument, PipelineResult
from pipeline.events import SectionReadyEvent, SectionStartedEvent
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
from textbook_agent.application.dtos import GenerationReport
from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.interface.api.app import app, create_app
from textbook_agent.interface.api.generation_recovery import (
    INTERRUPTED_GENERATION_ERROR_CODE,
    mark_stale_generations_failed,
)
from textbook_agent.interface.api.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_jwt_handler,
    get_report_repository,
    get_student_profile_repository,
    get_user_repository,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user
from textbook_agent.interface.api.routes import generation as generation_routes


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
        qc_reports=[],
        quality_passed=True if status == "completed" else None,
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now() if status == "completed" else None,
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

JWT_HANDLER = get_jwt_handler()
AUTH_HEADERS = {
    "Authorization": f"Bearer {JWT_HANDLER.create_access_token(TEST_USER.id, TEST_USER.email)}"
}


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestHealthAndAuth:
    async def test_health_returns_pipeline_runtime_metadata(self):
        with TestClient(create_app()) as client:
            response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["pipeline_architecture"] == "shell-pipeline-native-lectio"

    async def test_auth_me_returns_current_user(self):
        async with await _client() as client:
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
            "textbook_agent.interface.api.routes.generation.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "mode": "balanced",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 4,
                    },
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        assert response.status_code == 202
        payload = response.json()
        assert payload["mode"] == "balanced"
        assert payload["events_url"].endswith("/events")
        assert payload["report_url"].endswith("/report")
        generation = await GEN_REPO.find_by_id(payload["generation_id"])
        assert generation is not None
        assert generation.requested_template_id == "guided-concept-path"
        assert generation.requested_preset_id == "blue-classroom"
        assert generation.section_count == 4

    async def test_create_generation_rejects_invalid_template_pair(self):
        async with await _client() as client:
            response = await client.post(
                "/api/v1/generations",
                json={
                    "subject": "Calculus",
                    "context": "Explain limits",
                    "mode": "balanced",
                    "template_id": "guided-concept-path",
                    "preset_id": "minimal-light",
                    "section_count": 4,
                },
                headers=AUTH_HEADERS,
            )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

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

        async with await _client() as client:
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

        async with await _client() as client:
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

    async def test_generation_report_endpoint_returns_saved_report(self):
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

        async with await _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/report",
                headers=AUTH_HEADERS,
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["generation_id"] == generation_id
        assert payload["outcome"] == "partial"

    async def test_generation_report_endpoint_requires_ownership(self):
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

        async with await _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/report",
                headers=AUTH_HEADERS,
            )

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
        async with await _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/events?token={token}",
            )
        assert response.status_code == 200
        assert "event: complete" in response.text
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
        async with await _client() as client:
            response = await client.get(
                f"/api/v1/generations/{generation_id}/events?token={token}",
            )

        assert response.status_code == 200
        assert "event: error" in response.text
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
            "textbook_agent.interface.api.routes.generation.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "mode": "balanced",
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
            "textbook_agent.interface.api.routes.generation.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "mode": "balanced",
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

    async def test_enhance_generation_creates_child_from_draft_seed(self):
        source_id = "gen-draft"
        source_document = _document(source_id, mode="draft")
        path = await DOC_REPO.save_document(source_document)
        await GEN_REPO.create(
            Generation(
                id=source_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                mode="draft",
                status="completed",
                document_path=path,
                requested_template_id="guided-concept-path",
                resolved_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                resolved_preset_id="blue-classroom",
                section_count=1,
                quality_passed=None,
            )
        )

        async def fake_run_pipeline(command, on_event=None):
            assert command.seed_document is not None
            assert command.seed_document.sections[0].section_id == "s-01"
            return PipelineResult(
                document=_document(command.generation_id or "gen-child", mode="balanced"),
                completed_nodes=["curriculum_planner", "process_section", "qc_agent"],
                generation_time_seconds=0.01,
            )

        with patch(
            "textbook_agent.interface.api.routes.generation.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with await _client() as client:
                response = await client.post(
                    f"/api/v1/generations/{source_id}/enhance",
                    json={"mode": "balanced", "note": "Tighten the worked explanation."},
                    headers=AUTH_HEADERS,
                )
                await asyncio.sleep(0.05)

        assert response.status_code == 202
        payload = response.json()
        assert payload["source_generation_id"] == source_id
        assert payload["report_url"].endswith("/report")
        child = await GEN_REPO.find_by_id(payload["generation_id"])
        assert child is not None
        assert child.source_generation_id == source_id
        assert child.section_count == 1

    async def test_run_generation_job_marks_cancelled_task_failed(self):
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

        report = await REPORT_REPO.load_report(generation_id)
        assert report.status == "failed"
        assert report.outcome == "failed"
        assert report.quality_passed is False
        assert report.final_error is not None

    async def test_stale_generation_recovery_updates_generation_document_and_report(self):
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
        assert updated.error_code == INTERRUPTED_GENERATION_ERROR_CODE
        assert updated.quality_passed is False

        document = await DOC_REPO.load_document(updated.document_path or "")
        assert document.status == "failed"
        assert document.quality_passed is False

        report = await REPORT_REPO.load_report(generation_id)
        assert report.status == "failed"
        assert report.outcome == "failed"
        assert report.quality_passed is False
