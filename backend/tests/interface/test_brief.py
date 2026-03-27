from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from pipeline.types.requests import SectionPlan
from textbook_agent.application.dtos.brief import BriefRequest, GenerationSpec
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.interface.api.app import app
from textbook_agent.interface.api.dependencies import get_student_profile_repository
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user
from textbook_agent.interface.api.routes import brief as brief_routes


TEST_USER = User(
    id="brief-user-id",
    email="brief@example.com",
    name="Brief User",
    picture_url=None,
    has_profile=True,
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)

TEST_PROFILE = StudentProfile(
    id="brief-profile-id",
    user_id=TEST_USER.id,
    age=15,
    education_level="high_school",
    interests=["science", "writing"],
    learning_style="visual",
    preferred_notation="plain",
    prior_knowledge="basic algebra",
    goals="learn how ecosystems work",
    preferred_depth="standard",
    learner_description="Prefers clear examples and short explanations.",
    created_at="2026-03-25T00:00:00+00:00",
    updated_at="2026-03-25T00:00:00+00:00",
)


class StaticProfileRepo:
    def __init__(self, profile: StudentProfile | None) -> None:
        self.profile = profile

    async def find_by_user_id(self, user_id: str) -> StudentProfile | None:
        _ = user_id
        return self.profile


class FakeAgent:
    def __init__(self, *, model, output_type, system_prompt) -> None:
        self.model = model
        self.output_type = output_type
        self.system_prompt = system_prompt


async def _override_current_user() -> User:
    return TEST_USER


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _install_overrides(profile: StudentProfile | None) -> None:
    app.dependency_overrides[get_current_user] = _override_current_user

    async def override_profile_repo():
        return StaticProfileRepo(profile)

    app.dependency_overrides[get_student_profile_repository] = override_profile_repo


def _fake_live_safe_catalog() -> dict[str, SimpleNamespace]:
    return {
        "guided-concept-path": SimpleNamespace(
            id="guided-concept-path",
            name="Guided Concept Path",
            intent="teach one concept clearly",
            learner_fit=["secondary", "mixed-ability"],
        ),
        "timeline-narrative": SimpleNamespace(
            id="timeline-narrative",
            name="Timeline Narrative",
            intent="sequence events or developments",
            learner_fit=["secondary"],
        ),
    }


class TestBriefApi:
    async def test_brief_returns_generation_spec(self):
        _install_overrides(TEST_PROFILE)
        catalog = _fake_live_safe_catalog()
        brief = BriefRequest(
            intent="Teach ecosystems to year 9 students",
            audience="Year 9 mixed ability",
        )
        spec = GenerationSpec(
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            section_count=3,
            sections=[
                SectionPlan(section_id="section-1", position=1, title="What ecosystems are", focus="Define the idea.", role="intro"),
                SectionPlan(section_id="section-2", position=2, title="How parts interact", focus="Show relationships."),
                SectionPlan(section_id="section-3", position=3, title="Check understanding", focus="Close with a quick check.", role="practice"),
            ],
            warning=None,
            rationale="Guided concept path suits a compact concept lesson.",
            source_brief=brief,
        )

        async def fake_run_llm(**kwargs):
            return SimpleNamespace(output=spec, kwargs=kwargs)

        with (
            patch.object(brief_routes, "list_template_ids", return_value=list(catalog)),
            patch.object(
                brief_routes,
                "validate_preset_for_template",
                side_effect=lambda template_id, preset_id: template_id == "guided-concept-path" and preset_id == "blue-classroom",
            ),
            patch.object(brief_routes, "get_contract", side_effect=catalog.__getitem__),
            patch.object(brief_routes, "get_node_text_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "textbook_agent.application.services.brief_planner_service.Agent",
                FakeAgent,
            ),
        ):
            async with _client() as client:
                response = await client.post("/api/v1/brief", json=brief.model_dump())

        assert response.status_code == 200
        payload = response.json()
        assert payload["template_id"] == "guided-concept-path"
        assert payload["preset_id"] == "blue-classroom"
        assert payload["section_count"] == 3
        assert payload["source_brief"]["intent"] == brief.intent

    async def test_brief_filters_out_non_live_safe_templates(self):
        _install_overrides(TEST_PROFILE)
        catalog = _fake_live_safe_catalog()
        captured: dict[str, str] = {}

        async def fake_run_llm(**kwargs):
            captured["system_prompt"] = kwargs["agent"].system_prompt
            return SimpleNamespace(
                output=GenerationSpec(
                    template_id="guided-concept-path",
                    preset_id="blue-classroom",
                    section_count=3,
                    sections=[
                        SectionPlan(section_id="section-1", position=1, title="Intro", focus="Set the scene.", role="intro"),
                        SectionPlan(section_id="section-2", position=2, title="Explain", focus="Show the core idea."),
                        SectionPlan(section_id="section-3", position=3, title="Review", focus="Check understanding.", role="practice"),
                    ],
                    warning=None,
                    rationale="Guided concept path suits the brief.",
                    source_brief=BriefRequest(intent="Teach ecosystems", audience="Year 9"),
                )
            )

        with (
            patch.object(
                brief_routes,
                "list_template_ids",
                return_value=["guided-concept-path", "timeline-narrative"],
            ),
            patch.object(
                brief_routes,
                "validate_preset_for_template",
                side_effect=lambda template_id, preset_id: template_id == "guided-concept-path" and preset_id == "blue-classroom",
            ),
            patch.object(brief_routes, "get_contract", side_effect=catalog.__getitem__),
            patch.object(brief_routes, "get_node_text_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "textbook_agent.application.services.brief_planner_service.Agent",
                FakeAgent,
            ),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief",
                    json={"intent": "Teach ecosystems", "audience": "Year 9"},
                )

        assert response.status_code == 200
        assert "guided-concept-path" in captured["system_prompt"]
        assert "timeline-narrative" not in captured["system_prompt"]

    async def test_brief_falls_back_after_invalid_output(self):
        _install_overrides(TEST_PROFILE)
        catalog = _fake_live_safe_catalog()
        calls = 0

        async def failing_run_llm(**kwargs):
            nonlocal calls
            calls += 1
            raise ValueError("invalid json from model")

        with (
            patch.object(brief_routes, "list_template_ids", return_value=list(catalog)),
            patch.object(
                brief_routes,
                "validate_preset_for_template",
                side_effect=lambda template_id, preset_id: template_id == "guided-concept-path" and preset_id == "blue-classroom",
            ),
            patch.object(brief_routes, "get_contract", side_effect=catalog.__getitem__),
            patch.object(brief_routes, "get_node_text_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=failing_run_llm),
            patch(
                "textbook_agent.application.services.brief_planner_service.Agent",
                FakeAgent,
            ),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief",
                    json={"intent": "Teach ecosystems", "audience": "Year 9"},
                )

        assert response.status_code == 200
        payload = response.json()
        assert calls == 2
        assert payload["template_id"] == "guided-concept-path"
        assert payload["section_count"] == 3
        assert [section["title"] for section in payload["sections"]] == [
            "Core Idea",
            "Worked Example",
            "Check Understanding",
        ]

    async def test_brief_includes_profile_context(self):
        _install_overrides(TEST_PROFILE)
        catalog = _fake_live_safe_catalog()
        captured: dict[str, str] = {}

        async def fake_run_llm(**kwargs):
            captured["system_prompt"] = kwargs["agent"].system_prompt
            return SimpleNamespace(
                output=GenerationSpec(
                    template_id="guided-concept-path",
                    preset_id="blue-classroom",
                    section_count=3,
                    sections=[
                        SectionPlan(section_id="section-1", position=1, title="Intro", focus="Set the scene.", role="intro"),
                        SectionPlan(section_id="section-2", position=2, title="Explain", focus="Show the core idea."),
                        SectionPlan(section_id="section-3", position=3, title="Review", focus="Check understanding.", role="practice"),
                    ],
                    warning=None,
                    rationale="Guided concept path suits the brief.",
                    source_brief=BriefRequest(intent="Teach ecosystems", audience="Year 9"),
                )
            )

        with (
            patch.object(brief_routes, "list_template_ids", return_value=list(catalog)),
            patch.object(
                brief_routes,
                "validate_preset_for_template",
                side_effect=lambda template_id, preset_id: template_id == "guided-concept-path" and preset_id == "blue-classroom",
            ),
            patch.object(brief_routes, "get_contract", side_effect=catalog.__getitem__),
            patch.object(brief_routes, "get_node_text_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "textbook_agent.application.services.brief_planner_service.Agent",
                FakeAgent,
            ),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief",
                    json={"intent": "Teach ecosystems", "audience": "Year 9"},
                )

        assert response.status_code == 200
        assert "Grade band: secondary" in captured["system_prompt"]
        assert "Prefers clear examples and short explanations." in captured["system_prompt"]
