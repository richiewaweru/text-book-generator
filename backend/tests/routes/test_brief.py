from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.dependencies import get_student_profile_repository
from core.entities.student_profile import TeacherProfile
from core.entities.user import User
from generation.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_report_repository,
)
from generation.dtos.generation_request import GenerationAcceptedResponse
from pipeline.types.requests import SectionPlan
from pipeline.types.teacher_brief import TeacherBrief, TopicResolutionResult
from planning.models import PlanningGenerationSpec
from planning import routes as brief_routes


TEST_USER = User(
    id="brief-user-id",
    email="brief@example.com",
    name="Brief User",
    picture_url=None,
    has_profile=True,
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)

TEST_PROFILE = TeacherProfile(
    id="brief-profile-id",
    user_id=TEST_USER.id,
    teacher_role="teacher",
    subjects=["science"],
    default_grade_band="high_school",
    default_audience_description="Year 9 mixed ability science",
    curriculum_framework="KS3",
    classroom_context="Mixed prior knowledge and limited device access.",
    planning_goals="Faster planning and clearer scaffolds.",
    school_or_org_name="Riverside High",
    delivery_preferences={
        "tone": "supportive",
        "reading_level": "standard",
        "explanation_style": "balanced",
        "example_style": "everyday",
        "brevity": "balanced",
        "use_visuals": True,
        "print_first": False,
        "more_practice": False,
        "keep_short": False,
    },
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)


class StaticProfileRepo:
    def __init__(self, profile: TeacherProfile | None) -> None:
        self.profile = profile

    async def find_by_user_id(self, user_id: str) -> TeacherProfile | None:
        _ = user_id
        return self.profile


async def _override_current_user() -> User:
    return TEST_USER


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _install_overrides(profile: TeacherProfile | None) -> None:
    app.dependency_overrides[get_current_user] = _override_current_user

    async def override_profile_repo():
        return StaticProfileRepo(profile)

    async def override_generation_repo():
        return SimpleNamespace()

    async def override_document_repo():
        return SimpleNamespace()

    async def override_report_repo():
        return SimpleNamespace()

    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_generation_repository] = override_generation_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_report_repository] = override_report_repo


def _teacher_brief() -> TeacherBrief:
    return TeacherBrief(
        subject="Science",
        topic="Ecosystems",
        subtopic="Food webs in river ecosystems",
        learner_context="Year 9 mixed ability learners",
        intended_outcome="understand",
        resource_type="worksheet",
        supports=["visuals", "worked_examples"],
        depth="standard",
        teacher_notes="Use a local river example.",
    )


def _planning_spec() -> PlanningGenerationSpec:
    brief = _teacher_brief()
    return PlanningGenerationSpec.model_validate(
        {
            "id": "plan-123",
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
            "lesson_rationale": "This resource moves from setup into guided application.",
            "directives": {
                "tone_profile": "supportive",
                "reading_level": "standard",
                "explanation_style": "balanced",
                "example_style": "everyday",
                "scaffold_level": "medium",
                "brevity": "balanced",
            },
            "committed_budgets": {},
            "sections": [
                {
                    "id": "section-1",
                    "order": 1,
                    "role": "intro",
                    "title": "Start with a river food web",
                    "objective": "Frame the ecosystem with one local example.",
                    "focus_note": "Use the river example first.",
                    "selected_components": ["hook-hero"],
                    "visual_policy": None,
                    "generation_notes": None,
                    "rationale": "Open with a concrete example.",
                }
            ],
            "warning": None,
            "source_brief_id": "brief-123",
            "source_brief": brief.model_dump(mode="json"),
            "status": "draft",
        }
    )


class TestBriefApi:
    async def test_plan_from_brief_returns_planning_generation_spec(self):
        _install_overrides(TEST_PROFILE)
        spec = _planning_spec()

        async def fake_plan(self, brief, *, model, run_llm_fn, generation_id="", emit=None):
            _ = (brief, model, run_llm_fn, generation_id, emit)
            return spec

        with (
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm"),
            patch.object(brief_routes.PlanningService, "plan", new=fake_plan),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/plan",
                    json=_teacher_brief().model_dump(mode="json"),
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["template_id"] == "guided-concept-path"
        assert payload["source_brief"]["subtopic"] == "Food webs in river ecosystems"
        assert payload["template_decision"]["chosen_id"] == "worksheet"

    async def test_commit_brief_starts_generation_with_teacher_brief_context(self):
        _install_overrides(TEST_PROFILE)
        spec = _planning_spec()
        captured: dict[str, object] = {}

        async def fake_enqueue_generation(**kwargs):
            captured.update(kwargs)
            return GenerationAcceptedResponse(
                generation_id="gen-123",
                status="pending",
                events_url="/api/v1/generations/gen-123/events",
                document_url="/api/v1/generations/gen-123/document",
                report_url="/api/v1/generations/gen-123/report",
            )

        with (
            patch.object(brief_routes, "validate_preset_for_template", return_value=True),
            patch.object(brief_routes, "enqueue_generation", side_effect=fake_enqueue_generation),
            patch.object(
                brief_routes,
                "_pipeline_sections_from_planning_spec",
                return_value=[
                    SectionPlan(
                        section_id="section-1",
                        position=1,
                        title="Start with a river food web",
                        focus="Use the river example first.",
                        role="intro",
                    )
                ],
            ),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/commit",
                    json=spec.model_dump(mode="json"),
                )

        assert response.status_code == 200
        assert response.json()["generation_id"] == "gen-123"
        assert captured["subject"] == "Food webs in river ecosystems"
        assert "Resource type: worksheet" in str(captured["context"])
        assert '"status":"committed"' in captured["planning_spec_json"]

    async def test_commit_brief_rejects_invalid_template_preset_combination(self):
        _install_overrides(TEST_PROFILE)
        spec = _planning_spec()

        with patch.object(brief_routes, "validate_preset_for_template", return_value=False):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/commit",
                    json=spec.model_dump(mode="json"),
                )

        assert response.status_code == 422
        assert "Invalid template/preset combination" in response.json()["detail"]

    async def test_resolve_topic_returns_structured_subtopics(self):
        _install_overrides(TEST_PROFILE)

        async def fake_run_pipeline_llm(**kwargs):
            _ = kwargs
            return SimpleNamespace(
                output=TopicResolutionResult.model_validate(
                    {
                        "subject": "Math",
                        "topic": "Algebra",
                        "candidate_subtopics": [
                            {
                                "id": "two-step-equations",
                                "title": "Solving two-step equations",
                                "description": "Solve equations with two operations.",
                                "likely_grade_band": "middle school",
                            },
                            {
                                "id": "duplicate",
                                "title": "Solving two-step equations",
                                "description": "Duplicate title that should be removed.",
                                "likely_grade_band": "middle school",
                            },
                        ],
                        "needs_clarification": False,
                        "clarification_message": None,
                    }
                )
            )

        class FakeAgent:
            def __init__(self, *, model, output_type, system_prompt) -> None:
                self.model = model
                self.output_type = output_type
                self.system_prompt = system_prompt

        with (
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "get_planning_slot", return_value=SimpleNamespace(value="fast")),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_pipeline_llm),
            patch.object(brief_routes, "Agent", FakeAgent),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/resolve-topic",
                    json={"raw_topic": "Algebra", "learner_context": "Grade 7 mixed levels"},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["subject"] == "Math"
        assert len(payload["candidate_subtopics"]) == 1

    async def test_validate_brief_returns_deterministic_blockers_and_warnings(self):
        _install_overrides(TEST_PROFILE)

        async with _client() as client:
            response = await client.post(
                "/api/v1/brief/validate",
                json={
                    "brief": {
                        "subject": "Math",
                        "topic": "Algebra",
                        "subtopic": "Algebra",
                        "learner_context": "Grade 7 students, mixed levels",
                        "intended_outcome": "assess",
                        "resource_type": "exit_ticket",
                        "supports": ["worked_examples"],
                        "depth": "deep",
                    }
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["is_ready"] is False
        assert any(message["field"] == "subtopic" for message in payload["blockers"])
        assert any(message["field"] == "depth" for message in payload["warnings"])
