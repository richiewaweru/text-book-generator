from __future__ import annotations

# ruff: noqa: E402

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

_SMOKE_DB_PATH = Path(tempfile.gettempdir()) / "textbook-agent-phase5-smoke.db"
if _SMOKE_DB_PATH.exists():
    _SMOKE_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_SMOKE_DB_PATH.as_posix()}"
os.environ["RUN_MIGRATIONS_ON_STARTUP"] = "false"

from app import create_app
from core.auth.middleware import get_current_user
from core.dependencies import get_jwt_handler
from core.database.migrations import upgrade_database
from core.database.models import GenerationModel, LLMCallModel, StudentProfileModel, UserModel
from core.database.session import async_session_factory
from core.entities.user import User
from core.events import LLMCallStartedEvent, LLMCallSucceededEvent, event_bus
from pipeline.api import PipelineDocument, PipelineResult
from pipeline.events import SectionStartedEvent
from planning.models import PlanningRefinedSection, PlanningRefinementOutput

USER_ID = "phase5-smoke-user"
EMAIL = "phase5-smoke@example.com"
SMOKE_USER = User(
    id=USER_ID,
    email=EMAIL,
    name="Phase 5 Smoke",
    picture_url=None,
    has_profile=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)


async def seed_db() -> None:
    async with async_session_factory() as session:
        await session.execute(delete(LLMCallModel).where(LLMCallModel.user_id == USER_ID))
        await session.execute(delete(GenerationModel).where(GenerationModel.user_id == USER_ID))
        await session.execute(
            delete(StudentProfileModel).where(StudentProfileModel.user_id == USER_ID)
        )
        await session.execute(delete(UserModel).where(UserModel.id == USER_ID))
        session.add(UserModel(id=USER_ID, email=EMAIL, name="Phase 5 Smoke"))
        session.add(
            StudentProfileModel(
                id="phase5-smoke-profile",
                user_id=USER_ID,
                age=16,
                education_level="high_school",
                interests=json.dumps(["math"]),
                learning_style="visual",
                preferred_notation="plain",
                prior_knowledge="basic algebra",
                goals="understand limits",
                preferred_depth="standard",
                learner_description="Curious and steady",
            )
        )
        await session.commit()


async def cleanup_db() -> None:
    async with async_session_factory() as session:
        await session.execute(delete(LLMCallModel).where(LLMCallModel.user_id == USER_ID))
        await session.execute(delete(GenerationModel).where(GenerationModel.user_id == USER_ID))
        await session.execute(
            delete(StudentProfileModel).where(StudentProfileModel.user_id == USER_ID)
        )
        await session.execute(delete(UserModel).where(UserModel.id == USER_ID))
        await session.commit()


async def override_current_user():
    return SMOKE_USER


async def fake_run_pipeline(command, on_event=None):
    generation_id = command.generation_id
    await on_event(
        SectionStartedEvent(
            generation_id=generation_id,
            section_id="s-01",
            title="Intro",
            position=1,
        )
    )
    await on_event(
        LLMCallStartedEvent(
            trace_id=generation_id,
            generation_id=generation_id,
            node="curriculum_planner",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
        )
    )
    await on_event(
        LLMCallSucceededEvent(
            trace_id=generation_id,
            generation_id=generation_id,
            node="curriculum_planner",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
            latency_ms=1234.0,
            tokens_in=111,
            tokens_out=222,
            cost_usd=0.003,
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
            section_manifest=[{"section_id": "s-01", "title": "Intro", "position": 1}],
            sections=[],
            failed_sections=[],
            qc_reports=[],
            quality_passed=True,
        ),
        completed_nodes=["curriculum_planner"],
        generation_time_seconds=0.01,
    )


async def fake_planning_run_llm(
    *,
    trace_id=None,
    caller=None,
    slot=None,
    user_prompt=None,
    **kwargs,
):
    _ = kwargs
    section_count = (user_prompt or "").count("order=") or 1
    event_bus.publish(
        trace_id,
        LLMCallStartedEvent(
            trace_id=trace_id,
            caller=caller,
            slot=slot or "standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
        ),
    )
    event_bus.publish(
        trace_id,
        LLMCallSucceededEvent(
            trace_id=trace_id,
            caller=caller,
            slot=slot or "standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
            latency_ms=456.0,
            tokens_in=50,
            tokens_out=75,
            cost_usd=0.001,
        ),
    )
    return SimpleNamespace(
        output=PlanningRefinementOutput(
            lesson_rationale="Refined for smoke test.",
            sections=[
                PlanningRefinedSection(
                    title=f"Section {index + 1}",
                    rationale="Refined rationale.",
                )
                for index in range(section_count)
            ],
        )
    )


async def main() -> None:
    await asyncio.to_thread(upgrade_database)
    await seed_db()
    app = create_app()
    app.dependency_overrides[get_current_user] = override_current_user
    token = get_jwt_handler().create_access_token(USER_ID, EMAIL)

    try:
        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=fake_run_pipeline,
        ), patch("planning.routes.run_llm", side_effect=fake_planning_run_llm):
            async with app.router.lifespan_context(app):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    generation_response = await client.post(
                        "/api/v1/generations",
                        json={
                            "subject": "Calculus",
                            "context": "Explain limits",
                            "template_id": "guided-concept-path",
                            "preset_id": "blue-classroom",
                            "section_count": 1,
                        },
                    )
                    generation_payload = generation_response.json()
                    await asyncio.sleep(0.2)

                    events_response = await client.get(
                        generation_payload["events_url"] + f"?token={token}"
                    )
                    report_response = await client.get(generation_payload["report_url"])

                    brief_response = await client.post(
                        "/api/v1/brief/stream",
                        json={
                            "intent": "Teach limits",
                            "audience": "High school calculus students",
                            "prior_knowledge": "Basic algebra",
                            "extra_context": "Keep it concise.",
                        },
                    )
                    await asyncio.sleep(0.2)
                    usage_response = await client.get("/api/v1/telemetry/llm-usage")

        print(
            {
                "generation_status": generation_response.status_code,
                "events_status": events_response.status_code,
                "events_has_complete": "event: complete" in events_response.text,
                "report_status": report_response.status_code,
                "report_has_completed": report_response.json().get("status") == "completed",
                "brief_status": brief_response.status_code,
                "brief_has_plan_event": (
                    "event: plan_complete" in brief_response.text
                    or "event: plan_error" in brief_response.text
                ),
                "usage_status": usage_response.status_code,
                "usage_total_calls": usage_response.json().get("total_calls"),
            }
        )
    finally:
        app.dependency_overrides.clear()
        await cleanup_db()


if __name__ == "__main__":
    asyncio.run(main())
