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
from generation.dtos.generation_response import GenerationAcceptedResponse
from pipeline.types.requests import SectionPlan
from pipeline.types.teacher_brief import (
    TeacherBrief,
    TopicResolutionRequest,
    TopicResolutionResult,
)
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
        subtopics=["Food webs in river ecosystems"],
        grade_level="grade_9",
        grade_band="adult",
        class_profile={
            "reading_level": "below_grade",
            "language_support": "some_ell",
            "confidence": "low",
            "prior_knowledge": "new_topic",
            "pacing": "short_chunks",
            "learning_preferences": ["visual", "step_by_step"],
        },
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
                    "bridges_from": None,
                    "bridges_to": "Explain the local food web",
                    "terms_to_define": ["food web"],
                    "terms_assumed": [],
                    "practice_target": None,
                }
            ],
            "warning": None,
            "source_brief_id": "brief-123",
            "source_brief": brief.model_dump(mode="json"),
            "status": "draft",
        }
    )


class TestBriefApi:
    def test_topic_resolution_prompt_includes_grade_fields(self):
        prompt = brief_routes._topic_resolution_user_prompt(
            TopicResolutionRequest(
                raw_topic="Algebra",
                grade_level="grade_10",
                grade_band="high_school",
                learner_context="Grade 10 learners",
                class_profile={
                    "reading_level": "on_grade",
                    "language_support": "none",
                    "confidence": "mixed",
                    "prior_knowledge": "some_background",
                    "pacing": "normal",
                    "learning_preferences": ["visual"],
                },
            )
        )

        assert "Grade level: grade_10" in prompt
        assert "Grade band: high_school" in prompt
        assert "Class profile: reading=on_grade" in prompt

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
        assert payload["source_brief"]["subtopics"] == ["Food webs in river ecosystems"]
        assert payload["template_decision"]["chosen_id"] == "worksheet"
        assert payload["sections"][0]["bridges_to"] == "Explain the local food web"
        assert payload["sections"][0]["terms_to_define"] == ["food web"]

    async def test_commit_brief_starts_generation_with_teacher_brief_context(self):
        _install_overrides(TEST_PROFILE)
        spec = _planning_spec()
        spec.sections[0].practice_target = "Explain how energy moves through the river food web."
        captured: dict[str, object] = {}

        async def fake_enqueue_generation(**kwargs):
            captured.update(kwargs)
            return GenerationAcceptedResponse(
                generation_id="gen-123",
                status="pending",
                events_url="/api/v1/generations/gen-123/events",
                document_url="/api/v1/generations/gen-123/document",
                report_url="/api/v1/generations/gen-123/report",
                section_count=kwargs["section_count"],
                sections_with_visuals=kwargs["sections_with_visuals"],
                subtopics_covered=list(kwargs["subtopics_covered"]),
                warning=kwargs["planning_warning"],
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
        assert response.json()["section_count"] == 1
        assert response.json()["sections_with_visuals"] == 0
        assert response.json()["subtopics_covered"] == ["Food webs in river ecosystems"]
        assert response.json()["warning"] is None
        assert captured["subject"] == "Science"
        assert "Resource type: worksheet" in str(captured["context"])
        assert "Grade level: grade_9" in str(captured["context"])
        assert "Class profile: reading=below_grade" in str(captured["context"])
        assert "Introduces: food web" in str(captured["context"])
        assert "Practice: Explain how energy moves through the river food web." in str(captured["context"])
        assert captured["grade_band"] == "secondary"
        assert captured["learner_fit"] == "supported"
        assert '"status":"committed"' in captured["planning_spec_json"]

    def test_pipeline_sections_from_planning_spec_preserve_explicit_bridges(self):
        spec = PlanningGenerationSpec.model_validate(
            {
                **_planning_spec().model_dump(mode="json"),
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
                        "bridges_from": None,
                        "bridges_to": "Explain the producer-consumer link",
                        "terms_to_define": ["food web"],
                        "terms_assumed": [],
                        "practice_target": None,
                    },
                    {
                        "id": "section-2",
                        "order": 2,
                        "role": "practice",
                        "title": "Explain the producer-consumer link",
                        "objective": "Let learners explain how energy moves.",
                        "focus_note": "Energy moves from producers to consumers.",
                        "selected_components": ["practice-stack"],
                        "visual_policy": None,
                        "generation_notes": None,
                        "rationale": "Move into explanation and application.",
                        "bridges_from": "Start from the local river example",
                        "bridges_to": None,
                        "terms_to_define": ["producer", "consumer"],
                        "terms_assumed": ["food web"],
                        "practice_target": "Explain the producer-consumer link in the river example.",
                    },
                ],
            }
        )

        sections = brief_routes._pipeline_sections_from_planning_spec(spec)

        assert sections[0].bridges_to == "Explain the producer-consumer link"
        assert sections[1].bridges_from == "Start from the local river example"

    def test_pipeline_sections_from_planning_spec_synthesizes_missing_bridges_for_legacy_specs(self):
        spec = PlanningGenerationSpec.model_validate(
            {
                **_planning_spec().model_dump(mode="json"),
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
                    },
                    {
                        "id": "section-2",
                        "order": 2,
                        "role": "practice",
                        "title": "Explain the producer-consumer link",
                        "objective": "Let learners explain how energy moves.",
                        "focus_note": "Energy moves from producers to consumers.",
                        "selected_components": ["practice-stack"],
                        "visual_policy": None,
                        "generation_notes": None,
                        "rationale": "Move into explanation and application.",
                    },
                ],
            }
        )

        sections = brief_routes._pipeline_sections_from_planning_spec(spec)

        assert sections[0].bridges_to == "Explain the producer-consumer link"
        assert sections[1].bridges_from == "Start with a river food web"

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
                    json={
                        "raw_topic": "Algebra",
                        "grade_level": "grade_7",
                        "grade_band": "middle_school",
                        "learner_context": "Grade 7 mixed levels",
                        "class_profile": {
                            "reading_level": "mixed",
                            "language_support": "none",
                            "confidence": "mixed",
                            "prior_knowledge": "some_background",
                            "pacing": "normal",
                            "learning_preferences": [],
                        },
                    },
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
                        "subtopics": ["Algebra"],
                        "grade_level": "mixed",
                        "grade_band": "adult",
                        "class_profile": {
                            "reading_level": "below_grade",
                            "language_support": "many_ell",
                            "confidence": "low",
                            "prior_knowledge": "new_topic",
                            "pacing": "short_chunks",
                            "learning_preferences": ["step_by_step"],
                        },
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
        assert any(message["field"] == "subtopics" for message in payload["blockers"])
        assert any(message["field"] == "grade_level" for message in payload["warnings"])
        assert any(message["field"] == "depth" for message in payload["warnings"])

    async def test_review_brief_returns_pedagogical_warnings(self):
        _install_overrides(TEST_PROFILE)

        async def fake_review(brief):
            _ = brief
            return [
                {
                    "message": "Several subtopics with quick depth will be very shallow.",
                    "suggestion": "Use standard depth or fewer subtopics.",
                    "severity": "warning",
                }
            ]

        with patch.object(brief_routes, "_review_brief_with_llm", side_effect=fake_review):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/review",
                    json={"brief": _teacher_brief().model_dump(mode="json")},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["coherent"] is False
        assert payload["feasibility"] == {
            "subtopics_fit": True,
            "depth_adequate": True,
            "supports_compatible": True,
        }
        assert payload["warnings"][0]["severity"] == "warning"
        assert payload["warnings"][0]["suggestion"] == "Use standard depth or fewer subtopics."

    async def test_review_brief_returns_deterministic_feasibility_warnings(self):
        _install_overrides(TEST_PROFILE)

        quick_brief = _teacher_brief().model_copy(
            update={
                "subtopics": [
                    "Food webs in river ecosystems",
                    "Producer and consumer roles",
                    "Energy transfer",
                ],
                "depth": "quick",
            }
        )

        with patch.object(brief_routes, "_review_brief_with_llm", return_value=[]):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/review",
                    json={"brief": quick_brief.model_dump(mode="json")},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["coherent"] is False
        assert payload["feasibility"]["subtopics_fit"] is False
        assert payload["warnings"][0]["severity"] == "warning"
        assert "condensed coverage" in payload["warnings"][0]["message"].lower()

    async def test_review_brief_flags_atypical_supports_as_info(self):
        _install_overrides(TEST_PROFILE)

        support_heavy_brief = _teacher_brief().model_copy(
            update={
                "resource_type": "exit_ticket",
                "supports": ["worked_examples"],
            }
        )

        with patch.object(brief_routes, "_review_brief_with_llm", return_value=[]):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/review",
                    json={"brief": support_heavy_brief.model_dump(mode="json")},
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["coherent"] is True
        assert payload["feasibility"]["supports_compatible"] is False
        assert any(
            warning["severity"] == "info" and "unusual for this resource type" in warning["message"].lower()
            for warning in payload["warnings"]
        )
