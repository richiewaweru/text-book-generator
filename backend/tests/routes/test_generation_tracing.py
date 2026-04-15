from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from pipeline.api import PipelineDocument, PipelineResult
from pipeline.events import (
    CurriculumPlannedEvent,
    InteractionOutcomeEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    MediaPlanReadyEvent,
    SectionStartedEvent,
    event_bus,
)
from generation.dtos import GenerationReport
from generation import service as generation_service
from generation.entities.generation import Generation
from core.entities.student_profile import StudentProfile
from core.entities.user import User
from app import create_app
from generation.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_report_repository,
)
from core.database.session import get_async_session
from core.dependencies import get_student_profile_repository
from core.auth.middleware import get_current_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


TEST_USER = User(
    id="trace-user",
    email="trace@example.com",
    name="Trace User",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
)


PROFILE = StudentProfile(
    id="trace-profile",
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
        pass


class StaticProfileRepo:
    def __init__(self, profile: StudentProfile | None) -> None:
        self.profile = profile

    async def find_by_user_id(self, user_id: str) -> StudentProfile | None:
        _ = user_id
        return self.profile


class _ReportRouteSession:
    async def execute(self, statement):
        _ = statement

        class _Result:
            @staticmethod
            def first():
                return (TEST_USER.id,)

        return _Result()


@asynccontextmanager
async def _client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_generation_job_logs_llm_trace_events() -> None:
    generation_repo = InMemoryGenerationRepo()
    document_repo = InMemoryDocumentRepo()
    report_repo = InMemoryReportRepo()
    profile_repo = StaticProfileRepo(PROFILE)
    app = create_app()
    trace_events: list[tuple[str, object]] = []

    async def override_current_user():
        return TEST_USER

    async def override_generation_repo():
        return generation_repo

    async def override_document_repo():
        return document_repo

    async def override_profile_repo():
        return profile_repo

    async def override_report_repo():
        return report_repo

    async def override_async_session():
        yield _ReportRouteSession()

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[get_async_session] = override_async_session

    async def fake_run_pipeline(command, on_event=None):
        generation_id = command.generation_id or "trace-gen"
        await on_event(
            LLMCallStartedEvent(
                generation_id=generation_id,
                node="content_generator",
                slot="standard",
                family="anthropic",
                model_name="claude-sonnet-4-6",
                attempt=1,
                section_id="s-03",
            )
        )
        await on_event(
            LLMCallSucceededEvent(
                generation_id=generation_id,
                node="content_generator",
                slot="standard",
                family="anthropic",
                model_name="claude-sonnet-4-6",
                attempt=1,
                section_id="s-03",
                latency_ms=4321.0,
                tokens_in=1200,
                tokens_out=800,
                cost_usd=0.012345,
            )
        )
        return PipelineResult(
            document=PipelineDocument(
                generation_id=generation_id,
                subject=command.subject,
                context=command.context,
                template_id=command.template_id,
                preset_id=command.preset_id,
                status="completed",
                sections=[],
                section_manifest=[],
                qc_reports=[],
            ),
            completed_nodes=["curriculum_planner"],
            generation_time_seconds=0.01,
        )

    try:
        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ), patch.object(
            generation_service,
            "_log_trace_event",
            side_effect=lambda generation_id, event: trace_events.append((generation_id, event)),
        ):
            async with _client(app) as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 4,
                    },
                )
                await asyncio.sleep(0.1)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert len(trace_events) >= 2
    assert any(
        generation_id == response.json()["generation_id"]
        and isinstance(event, LLMCallStartedEvent)
        and event.node == "content_generator"
        and event.section_id == "s-03"
        for generation_id, event in trace_events
    )
    assert any(
        generation_id == response.json()["generation_id"]
        and isinstance(event, LLMCallSucceededEvent)
        and event.tokens_in == 1200
        and event.tokens_out == 800
        and event.latency_ms == 4321.0
        for generation_id, event in trace_events
    )
    report = await report_repo.load_report(response.json()["generation_id"])
    assert report.summary.total_tokens_in == 1200
    assert report.summary.total_tokens_out == 800


async def test_generation_report_captures_pipeline_and_direct_event_bus_events() -> None:
    generation_repo = InMemoryGenerationRepo()
    document_repo = InMemoryDocumentRepo()
    report_repo = InMemoryReportRepo()
    profile_repo = StaticProfileRepo(PROFILE)
    app = create_app()

    async def override_current_user():
        return TEST_USER

    async def override_generation_repo():
        return generation_repo

    async def override_document_repo():
        return document_repo

    async def override_profile_repo():
        return profile_repo

    async def override_report_repo():
        return report_repo

    async def override_async_session():
        yield _ReportRouteSession()

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[get_async_session] = override_async_session

    async def fake_run_pipeline(command, on_event=None):
        generation_id = command.generation_id or "trace-gen"
        await on_event(
            SectionStartedEvent(
                generation_id=generation_id,
                section_id="s-01",
                title="Intro section",
                position=1,
            )
        )
        event_bus.publish(
            generation_id,
            CurriculumPlannedEvent(
                generation_id=generation_id,
                path="seeded_enrichment",
                result="enriched",
                duplicate_term_warnings=["Duplicate term assignment in curriculum plan term='slope' first_section='s-01' duplicate_section='s-02'"],
                runtime_curriculum_outline=[
                    {
                        "section_id": "s-01",
                        "title": "Intro section",
                        "position": 1,
                        "role": "intro",
                        "focus": "Introduce slope as steepness on a graph.",
                        "terms_to_define": ["slope"],
                        "terms_assumed": [],
                        "practice_target": "identify slope as a measure of steepness",
                        "visual_commitment": "diagram",
                    }
                ],
                planner_trace_sections=[
                    {
                        "section_id": "s-01",
                        "title": "Intro section",
                        "position": 1,
                        "role": "intro",
                        "rationale_summary": "Introduce slope as steepness on a graph.",
                    }
                ],
            ),
        )
        event_bus.publish(
            generation_id,
            LLMCallStartedEvent(
                generation_id=generation_id,
                node="curriculum_planner",
                slot="fast",
                family="anthropic",
                model_name="claude-sonnet-4-6",
                attempt=1,
            ),
        )
        event_bus.publish(
            generation_id,
            LLMCallSucceededEvent(
                generation_id=generation_id,
                node="curriculum_planner",
                slot="fast",
                family="anthropic",
                model_name="claude-sonnet-4-6",
                attempt=1,
                latency_ms=1500.0,
                tokens_in=500,
                tokens_out=300,
                cost_usd=0.004,
            ),
        )
        event_bus.publish(
            generation_id,
            InteractionOutcomeEvent(
                generation_id=generation_id,
                section_id="s-01",
                outcome="skipped",
                skip_reason="no_plan",
            ),
        )
        event_bus.publish(
            generation_id,
            MediaPlanReadyEvent(
                generation_id=generation_id,
                section_id="s-01",
                slot_count=1,
            ),
        )
        return PipelineResult(
            document=PipelineDocument(
                generation_id=generation_id,
                subject=command.subject,
                context=command.context,
                template_id=command.template_id,
                preset_id=command.preset_id,
                status="completed",
                sections=[],
                section_manifest=[
                    {
                        "section_id": "s-01",
                        "title": "Intro section",
                        "position": 1,
                    }
                ],
                qc_reports=[],
            ),
            completed_nodes=["curriculum_planner"],
            generation_time_seconds=0.01,
        )

    try:
        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ):
            async with _client(app) as client:
                response = await client.post(
                    "/api/v1/generations",
                    json={
                        "subject": "Calculus",
                        "context": "Explain limits",
                        "template_id": "guided-concept-path",
                        "preset_id": "blue-classroom",
                        "section_count": 1,
                    },
                )
                await asyncio.sleep(0.1)
                report_response = await client.get(
                    f"/api/v1/generations/{response.json()['generation_id']}/report"
                )
    finally:
        app.dependency_overrides.clear()

    report = await report_repo.load_report(response.json()["generation_id"])
    timeline_types = [item.type for item in report.timeline]
    assert "section_started" in timeline_types
    assert "llm_call_started" in timeline_types
    assert "llm_call_succeeded" in timeline_types
    assert "interaction_outcome" in timeline_types
    assert "media_plan_ready" in timeline_types
    assert "curriculum_planned" in timeline_types
    assert report_response.status_code == 200
    assert report.runtime_curriculum_outline[0].section_id == "s-01"
    assert report.planner_trace is not None
    assert report.planner_trace.path == "seeded_enrichment"
    assert report.planner_trace.duplicate_term_warnings[0].startswith(
        "Duplicate term assignment in curriculum plan"
    )
    assert report_response.json()["sections"][0]["interaction_outcome"] == "skipped"
    assert report_response.json()["sections"][0]["interaction_skip_reason"] == "no_plan"
    assert report_response.json()["runtime_curriculum_outline"][0]["visual_commitment"] == "diagram"
    assert report_response.json()["planner_trace"]["result"] == "enriched"

