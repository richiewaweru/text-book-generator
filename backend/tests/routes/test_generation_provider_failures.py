from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from pydantic_ai.exceptions import UserError

from pipeline.api import PipelineDocument
from generation.dtos import GenerationReport
from generation.entities.generation import Generation
from core.entities.student_profile import StudentProfile
from core.entities.user import User
from app import create_app
from generation.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_report_repository,
)
from core.dependencies import get_student_profile_repository
from core.auth.middleware import get_current_user


def _now() -> datetime:
    return datetime.now(timezone.utc)


TEST_USER = User(
    id="provider-failure-user",
    email="provider@example.com",
    name="Provider Failure",
    picture_url=None,
    has_profile=True,
    created_at=_now(),
    updated_at=_now(),
)


PROFILE = StudentProfile(
    id="provider-profile",
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


def _planning_spec(*, section_count: int = 2) -> dict:
    sections = [
        {
            "id": f"section-{index}",
            "order": index,
            "role": role,
            "title": title,
            "objective": objective,
            "focus_note": objective,
            "selected_components": components,
            "visual_policy": None,
            "generation_notes": None,
            "rationale": objective,
        }
        for index, (role, title, objective, components) in enumerate(
            [
                (
                    "intro",
                    "Limits first look",
                    "Introduce the idea of approaching a value.",
                    ["hook-hero", "explanation-block"],
                ),
                (
                    "practice",
                    "Check understanding",
                    "Use practice to reinforce the concept.",
                    ["practice-stack", "what-next-bridge"],
                ),
            ][:section_count],
            start=1,
        )
    ]
    return {
        "id": "plan-provider-failure",
        "template_id": "guided-concept-path",
        "preset_id": "blue-classroom",
        "mode": "balanced",
        "template_decision": {
            "chosen_id": "worksheet",
            "chosen_name": "Worksheet",
            "rationale": "Teacher selected Worksheet.",
            "fit_score": 1.0,
            "alternatives": [],
        },
        "lesson_rationale": "Move from explanation into guided practice.",
        "directives": {
            "tone_profile": "supportive",
            "reading_level": "standard",
            "explanation_style": "balanced",
            "example_style": "everyday",
            "scaffold_level": "medium",
            "brevity": "balanced",
        },
        "committed_budgets": {},
        "sections": sections,
        "warning": None,
        "source_brief_id": "brief-provider-failure",
        "source_brief": {
            "subject": "Mathematics",
            "topic": "Limits",
            "subtopics": ["Understanding limits"],
            "grade_level": "grade_11",
            "grade_band": "adult",
            "class_profile": {
                "reading_level": "on_grade",
                "language_support": "none",
                "confidence": "mixed",
                "prior_knowledge": "some_background",
                "pacing": "normal",
                "learning_preferences": [],
            },
            "learner_context": "High school calculus students",
            "intended_outcome": "understand",
            "resource_type": "worksheet",
            "supports": [],
            "depth": "standard",
            "teacher_notes": None,
        },
        "status": "draft",
    }


@asynccontextmanager
async def _client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


async def test_create_generation_marks_provider_configuration_failures_as_provider_errors() -> None:
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

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_report_repository] = override_report_repo

    try:
        with patch(
            "pipeline.adapter.run_pipeline_streaming",
            side_effect=UserError(
                "Set the `ANTHROPIC_API_KEY` environment variable or pass it via "
                "`AnthropicProvider(api_key=...)` to use the Anthropic provider."
            ),
        ):
            async with _client(app) as client:
                response = await client.post(
                    "/api/v1/brief/commit",
                    json=_planning_spec(section_count=2),
                )
                await asyncio.sleep(0.05)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    generation = await generation_repo.find_by_id(response.json()["generation_id"])
    assert generation is not None
    assert generation.status == "failed"
    assert generation.error_type == "provider_error"
    assert generation.error_code == "provider_configuration_failed"
    assert generation.error is not None
    assert "ANTHROPIC_API_KEY" in generation.error
    report = await report_repo.load_report(response.json()["generation_id"])
    assert report.status == "failed"
    assert report.outcome == "failed"

