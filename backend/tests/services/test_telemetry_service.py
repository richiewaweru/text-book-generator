from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app import app
from core.auth.middleware import get_current_user
from core.dependencies import get_jwt_handler
from core.database.models import GenerationModel
from core.database.session import async_session_factory
from core.entities.user import User
from pipeline.api import PipelineDocument
from telemetry.dependencies import get_llm_call_repository
from telemetry.dtos.usage import LLMUsageBreakdownItem, LLMUsageResponse
from telemetry.service import TelemetryMonitor, telemetry_monitor


def _now() -> datetime:
    return datetime.now(timezone.utc)


TEST_USER = User(
    id="telemetry-user-id",
    email="telemetry@example.com",
    name="Telemetry User",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
)


@asynccontextmanager
async def _client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


class InMemoryReportRepo:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}

    async def save_report(self, report) -> str:
        self.store[report.generation_id] = report
        return f"memory://report/{report.generation_id}"

    async def load_report(self, generation_id: str):
        return self.store[generation_id]

    async def cleanup_tmp(self, generation_id: str) -> None:
        _ = generation_id


class RecordingLLMCallRepo:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def aggregate_usage(self, **kwargs) -> LLMUsageResponse:
        self.calls.append(kwargs)
        return LLMUsageResponse(
            total_calls=2,
            total_tokens_in=300,
            total_tokens_out=150,
            total_cost_usd=0.42,
            by_caller=[
                LLMUsageBreakdownItem(
                    key="planner",
                    calls=2,
                    tokens_in=300,
                    tokens_out=150,
                    cost_usd=0.42,
                )
            ],
            by_model=[
                LLMUsageBreakdownItem(
                    key="claude-sonnet-4-6",
                    calls=2,
                    tokens_in=300,
                    tokens_out=150,
                    cost_usd=0.42,
                )
            ],
            by_slot=[
                LLMUsageBreakdownItem(
                    key="standard",
                    calls=2,
                    tokens_in=300,
                    tokens_out=150,
                    cost_usd=0.42,
                )
            ],
        )


async def override_current_user():
    return TEST_USER


async def test_backfill_failed_reports_synthesizes_missing_failure_report() -> None:
    generation_id = "telemetry-backfill"
    document = PipelineDocument(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="failed",
        section_manifest=[
            {"section_id": "s-01", "title": "Intro", "position": 1},
            {"section_id": "s-02", "title": "Practice", "position": 2},
        ],
        sections=[],
        failed_sections=[],
        qc_reports=[],
        quality_passed=False,
        error="Interrupted generation",
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )

    async with async_session_factory() as session:
        await session.execute(
            delete(GenerationModel).where(GenerationModel.id == generation_id)
        )
        session.add(
            GenerationModel(
                id=generation_id,
                user_id=TEST_USER.id,
                subject="Calculus",
                context="Explain limits",
                requested_template_id="guided-concept-path",
                requested_preset_id="blue-classroom",
                status="failed",
                document_path=f"db://generations/{generation_id}/document",
                document_json=document.model_dump(mode="json"),
                report_json=None,
                section_count=2,
                quality_passed=False,
                error="Interrupted generation",
                completed_at=_now(),
            )
        )
        await session.commit()

    report_repo = InMemoryReportRepo()
    async def load_report_repo():
        return report_repo

    telemetry_monitor.configure(
        report_repository_factory=load_report_repo,
    )
    try:
        count = await telemetry_monitor.backfill_failed_reports()
    finally:
        telemetry_monitor.configure()
        async with async_session_factory() as session:
            await session.execute(
                delete(GenerationModel).where(GenerationModel.id == generation_id)
            )
            await session.commit()

    assert count == 1
    report = await report_repo.load_report(generation_id)
    assert report.status == "failed"
    assert report.outcome == "failed"
    assert report.summary.planned_sections == 2
    assert report.summary.failed_sections == 2
    assert report.runtime_curriculum_outline == []
    assert report.planner_trace is None


async def test_llm_usage_route_scopes_to_authenticated_user() -> None:
    repo = RecordingLLMCallRepo()
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_llm_call_repository] = lambda: repo

    jwt_handler = get_jwt_handler()
    headers = {
        "Authorization": (
            f"Bearer {jwt_handler.create_access_token(TEST_USER.id, TEST_USER.email)}"
        )
    }

    try:
        async with _client() as client:
            response = await client.get(
                "/api/v1/telemetry/llm-usage",
                params={
                    "caller": "planner",
                    "model_name": "claude-sonnet-4-6",
                    "slot": "standard",
                    "trace_id": "planning-trace-1",
                },
                headers=headers,
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_calls"] == 2
    assert payload["total_tokens_in"] == 300
    assert payload["by_caller"][0]["key"] == "planner"
    assert repo.calls == [
        {
            "user_id": TEST_USER.id,
            "date_from": None,
            "date_to": None,
            "caller": "planner",
            "model_name": "claude-sonnet-4-6",
            "slot": "standard",
            "trace_id": "planning-trace-1",
        }
    ]


async def test_v3_recorder_initializes_and_finalizes_on_resource_finalised() -> None:
    generation_id = "telemetry-v3-finalize"
    report_repo = InMemoryReportRepo()

    monitor = TelemetryMonitor()

    async def load_report_repo():
        return report_repo

    monitor.configure(report_repository_factory=load_report_repo)
    await monitor.initialise_v3_recorder(
        generation_id=generation_id,
        user_id=TEST_USER.id,
        blueprint_title="Triangles",
        subject="Mathematics",
        template_id="guided-concept-path",
    )
    await monitor._handle_event(  # noqa: SLF001
        {
            "type": "generation_complete",
            "generation_id": generation_id,
            "coherence_review": {"status": "repair_required", "blocking_count": 2},
        }
    )
    await monitor._handle_event(  # noqa: SLF001
        {
            "type": "resource_finalised",
            "generation_id": generation_id,
            "status": "passed_with_warnings",
        }
    )

    report = await report_repo.load_report(generation_id)
    assert report.pipeline_version == "v3"
    assert report.status == "completed"
    assert report.quality_passed is True
    assert report.coherence_review == {"status": "repair_required", "blocking_count": 2}
