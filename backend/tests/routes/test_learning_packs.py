from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app import app
from core.auth.middleware import get_current_user
from core.dependencies import get_student_profile_repository
from core.entities.user import User
from generation.dependencies import (
    get_document_repository,
    get_generation_engine,
    get_generation_repository,
    get_report_repository,
)
from learning import routes as learning_routes
from learning.models import LearningJob, LearningPackPlan, PackGenerateResponse, PackLearningPlan, ResourcePlan
from pipeline.types.teacher_brief import TeacherBrief


TEST_USER = User(
    id="packs-user-id",
    email="packs@example.com",
    name="Packs User",
    picture_url=None,
    has_profile=True,
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)


async def _override_current_user() -> User:
    return TEST_USER


def _teacher_brief() -> TeacherBrief:
    return TeacherBrief(
        subject="Science",
        topic="Food Webs",
        subtopics=["Energy transfer in river ecosystems"],
        grade_level="grade_7",
        grade_band="middle_school",
        class_profile={
            "reading_level": "below_grade",
            "language_support": "some_ell",
            "confidence": "low",
            "prior_knowledge": "new_topic",
            "pacing": "short_chunks",
            "learning_preferences": ["visual"],
        },
        learner_context="Grade 7 mixed-ability class with ELL learners.",
        intended_outcome="practice",
        resource_type="worksheet",
        supports=["worked_examples", "visuals"],
        depth="standard",
        teacher_notes="Use local examples.",
    )


def _pack_plan() -> LearningPackPlan:
    job = LearningJob(
        job="practice",
        subject="Science",
        topic="Food Webs",
        grade_level="grade_7",
        grade_band="middle_school",
        objective="Students can explain energy transfer in a food web.",
        class_signals=[],
        assumptions=[],
        warnings=[],
        recommended_depth="standard",
        inferred_supports=["worked_examples"],
        inferred_class_profile={},
    )
    return LearningPackPlan(
        pack_id="pack-test-123",
        learning_job=job,
        pack_learning_plan=PackLearningPlan(
            objective="Students can explain energy transfer in a food web.",
            success_criteria=[],
            prerequisite_skills=[],
            likely_misconceptions=[],
            shared_vocabulary=["producer", "consumer", "energy"],
            shared_examples=[],
        ),
        resources=[
            ResourcePlan(
                id="resource-1",
                order=1,
                resource_type="worksheet",
                intended_outcome="practice",
                label="Guided practice",
                purpose="Practice energy transfer reasoning.",
                depth="standard",
                supports=["worked_examples"],
                enabled=True,
            )
        ],
        pack_rationale="Practice-focused support for food webs.",
    )


def _install_overrides() -> None:
    app.dependency_overrides[get_current_user] = _override_current_user
    
    class StaticProfileRepo:
        async def find_by_user_id(self, _user_id):
            return None

    async def override_profile_repo():
        return StaticProfileRepo()

    async def override_engine():
        return SimpleNamespace()

    async def override_gen_repo():
        return SimpleNamespace()

    async def override_document_repo():
        return SimpleNamespace()

    async def override_report_repo():
        return SimpleNamespace()

    async def override_pack_repo():
        return SimpleNamespace()

    app.dependency_overrides[get_student_profile_repository] = override_profile_repo
    app.dependency_overrides[get_generation_engine] = override_engine
    app.dependency_overrides[get_generation_repository] = override_gen_repo
    app.dependency_overrides[get_document_repository] = override_document_repo
    app.dependency_overrides[get_report_repository] = override_report_repo
    app.dependency_overrides[learning_routes.get_pack_repository] = override_pack_repo


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestLearningPacksApi:
    def test_brief_to_learning_job_maps_outcome_and_signals(self):
        brief = _teacher_brief()
        job = learning_routes._brief_to_learning_job(brief)

        assert job.job == "practice"
        assert "below grade reading level" in job.class_signals
        assert "some ell students" in job.class_signals
        assert "low confidence" in job.class_signals
        assert "first exposure to this topic" in job.class_signals
        assert "needs shorter tasks" in job.class_signals

    async def test_pack_legacy_routes_are_removed(self):
        _install_overrides()

        async with _client() as client:
            interpret_response = await client.post(
                "/api/v1/packs/interpret",
                json={"situation": "Grade 7 learners need a practice pack."},
            )
            plan_response = await client.post(
                "/api/v1/packs/plan",
                json={},
            )

        assert interpret_response.status_code in {404, 405}
        assert plan_response.status_code in {404, 405}

    async def test_plan_from_brief_returns_pack_plan(self):
        _install_overrides()
        brief = _teacher_brief()
        returned_plan = _pack_plan()

        async def fake_generate_pack_learning_plan(*args, **kwargs):
            _ = (args, kwargs)
            return returned_plan.pack_learning_plan

        with (
            patch.object(learning_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(learning_routes, "build_model", return_value=object()),
            patch.object(learning_routes, "generate_pack_learning_plan", side_effect=fake_generate_pack_learning_plan),
            patch.object(learning_routes, "plan_pack", return_value=returned_plan),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/packs/plan-from-brief",
                    json=brief.model_dump(mode="json"),
                )

        assert response.status_code == 200
        payload = response.json()
        assert payload["pack_id"] == "pack-test-123"
        assert payload["learning_job"]["job"] == "practice"
        assert payload["pack_learning_plan"]["objective"] == returned_plan.pack_learning_plan.objective

    async def test_plan_from_brief_falls_back_when_pack_planning_fails(self):
        _install_overrides()
        brief = _teacher_brief()
        captured: dict[str, object] = {}

        def fake_plan_pack(job, pack_learning_plan):
            captured["job"] = job
            captured["plan"] = pack_learning_plan
            return _pack_plan().model_copy(
                update={
                    "learning_job": job,
                    "pack_learning_plan": pack_learning_plan,
                }
            )

        with (
            patch.object(learning_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(learning_routes, "build_model", return_value=object()),
            patch.object(learning_routes, "generate_pack_learning_plan", side_effect=RuntimeError("LLM failed")),
            patch.object(learning_routes, "plan_pack", side_effect=fake_plan_pack),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/packs/plan-from-brief",
                    json=brief.model_dump(mode="json"),
                )

        assert response.status_code == 200
        fallback_plan = captured["plan"]
        assert isinstance(fallback_plan, PackLearningPlan)
        assert fallback_plan.objective == "Energy transfer in river ecosystems"
        assert fallback_plan.shared_vocabulary == []

    async def test_generate_uses_learner_context_and_rejects_legacy_situation(self):
        _install_overrides()
        plan = _pack_plan()
        captured: dict[str, str] = {}

        async def fake_start_pack(pack, learner_context, **kwargs):
            _ = (pack, kwargs)
            captured["learner_context"] = learner_context
            return PackGenerateResponse(pack_id="pack-test-123", status="running")

        with (
            patch.object(learning_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(learning_routes, "build_model", return_value=object()),
            patch.object(learning_routes, "start_pack", side_effect=fake_start_pack),
        ):
            async with _client() as client:
                success_response = await client.post(
                    "/api/v1/packs/generate",
                    json={
                        "pack_plan": plan.model_dump(mode="json"),
                        "learner_context": "Grade 7 students need scaffolded practice.",
                    },
                )
                legacy_response = await client.post(
                    "/api/v1/packs/generate",
                    json={
                        "pack_plan": plan.model_dump(mode="json"),
                        "situation": "Legacy payload",
                    },
                )

        assert success_response.status_code == 200
        assert captured["learner_context"] == "Grade 7 students need scaffolded practice."
        assert legacy_response.status_code == 422
