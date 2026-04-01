from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from planning.models import PlanningGenerationSpec, PlanningTemplateContract, StudioBriefRequest
from pipeline.types.requests import SectionPlan
from planning.dtos import BriefRequest, GenerationSpec
from generation.dtos.generation_request import GenerationAcceptedResponse
from core.entities.student_profile import StudentProfile
from core.entities.user import User
from app import app
from generation.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_report_repository,
)
from core.dependencies import get_student_profile_repository
from core.auth.middleware import get_current_user
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


def _fake_live_safe_catalog() -> dict[str, SimpleNamespace]:
    return {
        "guided-concept-path": SimpleNamespace(
            id="guided-concept-path",
            name="Guided Concept Path",
            intent="teach one concept clearly",
            learner_fit=["secondary", "mixed-ability"],
        ),
        "timeline": SimpleNamespace(
            id="timeline",
            name="Timeline",
            intent="sequence events or developments",
            learner_fit=["secondary"],
        ),
    }


def _planning_contract() -> PlanningTemplateContract:
    return PlanningTemplateContract(
        id="guided-concept-path",
        name="Guided Concept Path",
        family="guided-concept",
        intent="introduce-concept",
        tagline="Lead with need, then explain.",
        reading_style="linear-guided",
        interaction_level="medium",
        lesson_flow=["Hook", "Explain", "Practice", "What next"],
        required_components=["section-header", "hook-hero", "practice-stack"],
        optional_components=["diagram-block"],
        always_present=["section-header", "hook-hero", "what-next-bridge"],
        available_components=[
            "section-header",
            "hook-hero",
            "practice-stack",
            "what-next-bridge",
            "diagram-block",
        ],
        component_budget={"practice-stack": 1},
        max_per_section={"practice-stack": 1},
        default_behaviours={},
        section_role_defaults={
            "intro": ["hook-hero"],
            "explain": ["diagram-block"],
            "practice": ["practice-stack"],
            "summary": ["what-next-bridge"],
        },
        signal_affinity={
            "topic_type": {"concept": 0.9},
            "learning_outcome": {"understand-why": 0.9},
            "class_style": {},
            "format": {"both": 0.8},
        },
        layout_notes=[],
        responsive_rules=[],
        print_rules=[],
        allowed_presets=["blue-classroom"],
        why_this_template_exists="Baseline teaching template.",
        generation_guidance={
            "tone": "clear",
            "pacing": "steady",
            "chunking": "medium",
            "emphasis": "explain first",
            "avoid": ["overload"],
        },
    )


def _studio_brief() -> StudioBriefRequest:
    return StudioBriefRequest(
        intent="Teach ecosystems to Year 9 students",
        audience="Year 9 mixed ability",
        prior_knowledge="Basic food chains",
        extra_context="Use a river ecosystem example.",
        signals={
            "topic_type": "concept",
            "learning_outcome": "understand-why",
            "class_style": ["engages-with-visuals"],
            "format": "both",
        },
        preferences={
            "tone": "supportive",
            "reading_level": "standard",
            "explanation_style": "balanced",
            "example_style": "everyday",
            "brevity": "balanced",
        },
        constraints={
            "more_practice": False,
            "keep_short": False,
            "use_visuals": True,
            "print_first": False,
        },
    )


def _planning_spec() -> PlanningGenerationSpec:
    return PlanningGenerationSpec(
        id="plan-123",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        template_decision={
            "chosen_id": "guided-concept-path",
            "chosen_name": "Guided Concept Path",
            "rationale": "Best fit for first exposure.",
            "fit_score": 0.93,
            "alternatives": [],
        },
        lesson_rationale="This structure introduces the concept before guided practice.",
        directives={
            "tone_profile": "supportive",
            "reading_level": "standard",
            "explanation_style": "balanced",
            "example_style": "everyday",
            "scaffold_level": "medium",
            "brevity": "balanced",
        },
        committed_budgets={"practice-stack": 1},
        sections=[
            {
                "id": "section-1",
                "order": 1,
                "role": "intro",
                "title": "Why ecosystems matter",
                "objective": "Frame the lesson with a concrete setting.",
                "focus_note": "Open with a local river example.",
                "selected_components": ["hook-hero"],
                "visual_policy": {
                    "required": True,
                    "intent": "show_realism",
                    "mode": "image",
                    "goal": "Anchor the topic in a real ecosystem.",
                    "style_notes": "Natural classroom-safe reference image.",
                },
                "generation_notes": None,
                "rationale": "Start with a vivid example.",
            }
        ],
        warning=None,
        source_brief_id="brief-123",
        source_brief=_studio_brief(),
        status="draft",
    )


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
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "planning.service.Agent",
                FakeAgent,
            ),
        ):
            async with _client() as client:
                response = await client.post("/api/v1/brief", json=brief.model_dump())

        assert response.status_code == 200
        payload = response.json()
        assert payload["template_id"] == "guided-concept-path"
        assert payload["preset_id"] == "blue-classroom"
        assert payload["mode"] == "balanced"
        assert payload["section_count"] == 3
        assert payload["source_brief"]["intent"] == brief.intent
        assert payload["source_brief"]["mode"] == "balanced"
        assert response.headers["Deprecation"] == "true"
        assert "/api/v1/brief/stream" in response.headers["Warning"]
        assert "/api/v1/brief/commit" in response.headers["Warning"]

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
                return_value=["guided-concept-path", "timeline"],
            ),
            patch.object(
                brief_routes,
                "validate_preset_for_template",
                side_effect=lambda template_id, preset_id: template_id == "guided-concept-path" and preset_id == "blue-classroom",
            ),
            patch.object(brief_routes, "get_contract", side_effect=catalog.__getitem__),
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "planning.service.Agent",
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
        assert "timeline" not in captured["system_prompt"]

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
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=failing_run_llm),
            patch(
                "planning.service.Agent",
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
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm", side_effect=fake_run_llm),
            patch(
                "planning.service.Agent",
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

    async def test_contracts_lists_live_safe_planning_contracts(self):
        _install_overrides(TEST_PROFILE)
        contract = _planning_contract()

        with patch.object(brief_routes, "_planning_live_safe_templates", return_value=[contract]):
            async with _client() as client:
                response = await client.get("/api/v1/contracts")

        assert response.status_code == 200
        payload = response.json()
        assert payload[0]["id"] == "guided-concept-path"
        assert payload[0]["available_components"] == [
            "section-header",
            "hook-hero",
            "practice-stack",
            "what-next-bridge",
            "diagram-block",
        ]
        assert payload[0]["signal_affinity"]["topic_type"]["concept"] == 0.9

    async def test_stream_brief_emits_template_section_and_complete_events(self):
        _install_overrides(TEST_PROFILE)
        contract = _planning_contract()
        spec = _planning_spec()

        async def fake_plan(
            self,
            brief,
            *,
            contracts,
            model,
            run_llm_fn,
            generation_id="",
            emit=None,
        ):
            _ = (brief, contracts, model, run_llm_fn, generation_id)
            assert emit is not None
            await emit(
                {
                    "event": "template_selected",
                    "data": {
                        "template_decision": spec.template_decision.model_dump(mode="json"),
                        "lesson_rationale": spec.lesson_rationale,
                        "warning": spec.warning,
                    },
                }
            )
            await emit(
                {
                    "event": "section_planned",
                    "data": {"section": spec.sections[0].model_dump(mode="json")},
                }
            )
            return spec

        with (
            patch.object(brief_routes, "_planning_live_safe_templates", return_value=[contract]),
            patch.object(brief_routes, "get_planning_spec", return_value=SimpleNamespace()),
            patch.object(brief_routes, "build_model", return_value=object()),
            patch.object(brief_routes, "run_llm"),
            patch.object(brief_routes.PlanningService, "plan", new=fake_plan),
        ):
            async with _client() as client:
                response = await client.post(
                    "/api/v1/brief/stream",
                    json=_studio_brief().model_dump(mode="json"),
                )

        assert response.status_code == 200
        assert "event: template_selected" in response.text
        assert "event: section_planned" in response.text
        assert "event: plan_complete" in response.text
        assert '"mode": "balanced"' in response.text
        assert "Why ecosystems matter" in response.text

    async def test_commit_brief_starts_generation_with_committed_planning_spec(self):
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
                "_context_from_planning_spec",
                return_value="Reviewed lesson plan",
            ),
            patch.object(
                brief_routes,
                "_pipeline_sections_from_planning_spec",
                return_value=[
                    SectionPlan(
                        section_id="section-1",
                        position=1,
                        title="Why ecosystems matter",
                        focus="Open with a river ecosystem example.",
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
        assert captured["subject"] == "Teach ecosystems to Year 9 students"
        assert captured["context"] == "Reviewed lesson plan"
        assert captured["mode"] == spec.mode
        assert captured["template_id"] == "guided-concept-path"
        assert len(captured["section_plans"]) == 1
        assert '"mode":"balanced"' in captured["planning_spec_json"]
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

    async def test_brief_rejects_oversized_intent_before_planning(self):
        _install_overrides(TEST_PROFILE)

        async with _client() as client:
            response = await client.post(
                "/api/v1/brief",
                json={"intent": "x" * 201, "audience": "Year 9"},
            )

        assert response.status_code == 422

    async def test_stream_brief_rejects_oversized_prior_knowledge_before_llm(self):
        _install_overrides(TEST_PROFILE)
        brief = _studio_brief().model_copy(update={"prior_knowledge": "x" * 1001})

        async with _client() as client:
            response = await client.post(
                "/api/v1/brief/stream",
                json=brief.model_dump(mode="json"),
            )

        assert response.status_code == 422

