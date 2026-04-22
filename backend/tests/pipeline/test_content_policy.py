from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from generation import service as generation_service
from planning import routes as planning_routes
from planning.models import PlanningSectionPlan
from pipeline.nodes import content_generator as content_generator_mod
from pipeline.nodes import curriculum_planner as curriculum_planner_mod
from pipeline.prompts.content import (
    ENRICHMENT_FIELDS,
    _section_plan_policy_block,
    _visual_context_block,
    build_content_user_prompt,
    build_core_user_prompt,
    build_enrichment_user_prompt,
    build_practice_user_prompt,
)
from pipeline.state import TextbookPipelineState
from pipeline.types.content_phases import (
    CoreContent,
    EnrichmentPhaseContent,
    PracticePhaseContent,
)
from pipeline.types.requests import GenerationMode, PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    DefinitionContent,
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionHeaderContent,
    WhatNextContent,
)
from pipeline.types.template_contract import GenerationGuidance, TemplateContractSummary


class FakeAgent:
    def __init__(self, *, model, output_type, system_prompt) -> None:
        self.model = model
        self.output_type = output_type
        self.system_prompt = system_prompt


def _guidance() -> GenerationGuidance:
    return GenerationGuidance(
        tone="clear",
        pacing="steady",
        chunking="medium",
        emphasis="explanation first",
        avoid=["long prose"],
    )


def _contract(**overrides) -> TemplateContractSummary:
    defaults = dict(
        id="guided-concept-path",
        name="Guided Concept Path",
        family="guided-concept",
        intent="introduce-concept",
        tagline="test",
        lesson_flow=["Hook", "Explain", "Practice"],
        required_components=[
            "section-header",
            "hook-hero",
            "explanation-block",
            "practice-stack",
            "what-next-bridge",
        ],
        optional_components=["definition-card"],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["science"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
    )
    defaults.update(overrides)
    return TemplateContractSummary(**defaults)


def _request(**overrides) -> PipelineRequest:
    defaults = dict(
        context="Photosynthesis basics",
        subject="Science",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=2,
        mode=GenerationMode.BALANCED,
        generation_id="gen-policy",
    )
    defaults.update(overrides)
    return PipelineRequest(**defaults)


def _section_plan(**overrides) -> SectionPlan:
    defaults = dict(
        section_id="s-01",
        title="Photosynthesis basics",
        position=1,
        focus="Introduce the core idea.",
        role="intro",
        required_components=[
            "section-header",
            "hook-hero",
            "explanation-block",
            "practice-stack",
            "what-next-bridge",
            "definition-card",
        ],
        optional_components=[],
    )
    defaults.update(overrides)
    return SectionPlan(**defaults)


def _base_state(**overrides) -> TextbookPipelineState:
    defaults = dict(
        request=_request(),
        contract=_contract(),
        current_section_id="s-01",
        current_section_plan=_section_plan(),
        curriculum_outline=[_section_plan(), _section_plan(section_id="s-02", title="Practice plants", position=2)],
    )
    defaults.update(overrides)
    return TextbookPipelineState(**defaults)


def test_section_plan_and_planning_section_plan_accept_legacy_payloads() -> None:
    plan = SectionPlan.model_validate(
        {
            "section_id": "s-01",
            "title": "Intro",
            "position": 1,
            "focus": "Set the scene.",
        }
    )
    planning_section = PlanningSectionPlan.model_validate(
        {
            "id": "section-1",
            "order": 1,
            "role": "intro",
            "title": "Intro",
            "selected_components": ["hook-hero"],
            "rationale": "Lead with context.",
        }
    )

    assert plan.terms_to_define == []
    assert plan.terms_assumed == []
    assert plan.practice_target is None
    assert plan.visual_commitment is None
    assert planning_section.terms_to_define == []
    assert planning_section.terms_assumed == []
    assert planning_section.practice_target is None
    assert planning_section.visual_commitment is None


def test_planning_to_pipeline_adapters_forward_policy_fields() -> None:
    planning_section = PlanningSectionPlan(
        id="section-1",
        order=1,
        role="intro",
        title="Intro",
        selected_components=["hook-hero"],
        rationale="Lead with context.",
        terms_to_define=["chlorophyll"],
        terms_assumed=["cell"],
        practice_target="identify chlorophyll's role in absorbing light",
        visual_commitment="diagram",
    )

    planning_route_plan = planning_routes._pipeline_section_from_planning(
        planning_section,
        always_present=[],
        generation_mode=GenerationMode.BALANCED,
    )
    generation_service_plan = generation_service._pipeline_section_from_planning(
        planning_section,
        always_present=[],
        generation_mode=GenerationMode.BALANCED,
    )

    assert planning_route_plan.terms_to_define == ["chlorophyll"]
    assert planning_route_plan.terms_assumed == ["cell"]
    assert planning_route_plan.practice_target == "identify chlorophyll's role in absorbing light"
    assert planning_route_plan.visual_commitment == "diagram"
    assert generation_service_plan.terms_to_define == ["chlorophyll"]
    assert generation_service_plan.terms_assumed == ["cell"]
    assert generation_service_plan.practice_target == "identify chlorophyll's role in absorbing light"
    assert generation_service_plan.visual_commitment == "diagram"


def test_policy_and_visual_prompt_blocks_include_new_fields() -> None:
    plan = _section_plan(
        terms_to_define=["chlorophyll"],
        terms_assumed=["leaf"],
        practice_target="apply the chlorophyll definition to explain light capture",
        visual_commitment="interaction",
    )

    policy = _section_plan_policy_block(plan)
    visual = _visual_context_block(plan)

    assert "terms_to_define: chlorophyll" in policy
    assert "terms_assumed: leaf" in policy
    assert "practice_target: apply the chlorophyll definition" in policy
    assert "visual_commitment: interaction" in policy
    assert "interactive above" in visual


@pytest.mark.parametrize(
    ("commitment", "expected"),
    [
        ("diagram", "diagram below"),
        ("interaction", "interactive above"),
        ("none", "NO diagram or interactive"),
    ],
)
def test_visual_context_is_injected_into_all_prompt_builders(
    commitment: str,
    expected: str,
) -> None:
    plan = _section_plan(visual_commitment=commitment)

    monolithic = build_content_user_prompt(
        section_plan=plan,
        subject="Science",
        context="Photosynthesis",
        grade_band="secondary",
        learner_fit="general",
        template_id="guided-concept-path",
    )
    core = build_core_user_prompt(
        section_plan=plan,
        subject="Science",
        context="Photosynthesis",
        grade_band="secondary",
        learner_fit="general",
        template_id="guided-concept-path",
    )
    practice = build_practice_user_prompt(
        section_plan=plan,
        subject="Science",
        context="Photosynthesis",
        grade_band="secondary",
        learner_fit="general",
        template_id="guided-concept-path",
        core_summary="Summary",
    )
    enrichment = build_enrichment_user_prompt(
        section_plan=plan,
        subject="Science",
        context="Photosynthesis",
        grade_band="secondary",
        learner_fit="general",
        template_id="guided-concept-path",
        core_summary="Summary",
        active_enrichment_fields=["definition"],
    )

    assert expected in monolithic
    assert expected in core
    assert expected in practice
    assert expected in enrichment


def test_visual_context_block_omits_text_for_legacy_none() -> None:
    assert _visual_context_block(_section_plan()) == ""


def test_enrichment_fields_include_new_text_components() -> None:
    assert {
        "callout",
        "summary",
        "student_textbox",
        "short_answer",
        "fill_in_blank",
        "divider",
        "key_fact",
    } <= ENRICHMENT_FIELDS


@pytest.mark.asyncio
async def test_curriculum_planner_enriches_seeded_outline_without_changing_structure(monkeypatch) -> None:
    outline = [
        _section_plan(section_id="s-01", title="Intro plants", position=1, role="intro"),
        _section_plan(section_id="s-02", title="Practice plants", position=2, role="practice"),
    ]
    state = _base_state(
        request=_request(section_plans=outline),
        current_section_plan=None,
    )

    async def fake_run_llm(**kwargs):
        return SimpleNamespace(
            output=curriculum_planner_mod.CurriculumEnrichmentOutput(
                sections=[
                    curriculum_planner_mod.SectionPlanEnrichment(
                        section_id="s-01",
                        terms_to_define=["chlorophyll"],
                        terms_assumed=[],
                        practice_target="name chlorophyll and what it does",
                        visual_commitment="diagram",
                    ),
                    curriculum_planner_mod.SectionPlanEnrichment(
                        section_id="s-02",
                        terms_to_define=[],
                        terms_assumed=["chlorophyll"],
                        practice_target="apply chlorophyll knowledge to explain leaf color",
                        visual_commitment="none",
                    ),
                ]
            )
        )

    monkeypatch.setattr(curriculum_planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(curriculum_planner_mod, "run_llm", fake_run_llm)
    monkeypatch.setattr(curriculum_planner_mod, "get_node_text_model", lambda *args, **kwargs: "fast-model")
    published_events: list[object] = []
    monkeypatch.setattr(
        curriculum_planner_mod,
        "publish_runtime_event",
        lambda generation_id, event: published_events.append(event),
    )

    result = await curriculum_planner_mod.curriculum_planner(state)

    enriched = result["curriculum_outline"]
    assert [section.title for section in enriched] == ["Intro plants", "Practice plants"]
    assert [section.role for section in enriched] == ["intro", "practice"]
    assert enriched[0].terms_to_define == ["chlorophyll"]
    assert enriched[1].terms_assumed == ["chlorophyll"]
    assert enriched[1].visual_commitment == "none"
    planner_event = next(event for event in published_events if event.type == "curriculum_planned")
    assert planner_event.path == "seeded_enrichment"
    assert planner_event.result == "enriched"
    assert planner_event.runtime_curriculum_outline[0].terms_to_define == ["chlorophyll"]
    assert planner_event.planner_trace_sections[0].rationale_summary == "Introduce the core idea."


@pytest.mark.asyncio
async def test_curriculum_planner_seeded_enrichment_failure_falls_back_to_outline(monkeypatch) -> None:
    outline = [_section_plan(section_id="s-01", title="Intro plants", position=1)]
    state = _base_state(
        request=_request(section_plans=outline),
        current_section_plan=None,
        curriculum_outline=None,
    )

    async def failing_run_llm(**kwargs):
        raise RuntimeError("planner enrichment unavailable")

    monkeypatch.setattr(curriculum_planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(curriculum_planner_mod, "run_llm", failing_run_llm)
    monkeypatch.setattr(curriculum_planner_mod, "get_node_text_model", lambda *args, **kwargs: "fast-model")
    published_events: list[object] = []
    monkeypatch.setattr(
        curriculum_planner_mod,
        "publish_runtime_event",
        lambda generation_id, event: published_events.append(event),
    )

    result = await curriculum_planner_mod.curriculum_planner(state)

    restored = result["curriculum_outline"]
    assert restored[0].title == "Intro plants"
    assert restored[0].terms_to_define == []
    assert restored[0].visual_commitment is None
    planner_event = next(event for event in published_events if event.type == "curriculum_planned")
    assert planner_event.path == "seeded_enrichment"
    assert planner_event.result == "fallback"
    assert planner_event.runtime_curriculum_outline[0].visual_commitment is None


@pytest.mark.asyncio
async def test_curriculum_planner_fresh_path_preserves_policy_fields(monkeypatch) -> None:
    state = _base_state(
        request=_request(section_plans=None),
        current_section_plan=None,
        curriculum_outline=None,
    )

    async def fake_run_llm(**kwargs):
        return SimpleNamespace(
            output=curriculum_planner_mod.CurriculumOutput(
                sections=[
                    _section_plan(
                        section_id="s-01",
                        position=1,
                        terms_to_define=["chlorophyll"],
                        terms_assumed=[],
                        practice_target="name the role of chlorophyll",
                        visual_commitment="diagram",
                    ),
                    _section_plan(
                        section_id="s-02",
                        position=2,
                        title="Repeat chlorophyll",
                        terms_to_define=["Chlorophyll"],
                        terms_assumed=[],
                        practice_target="spot the repeated term",
                        visual_commitment="none",
                    )
                ]
            )
        )

    monkeypatch.setattr(curriculum_planner_mod, "Agent", FakeAgent)
    monkeypatch.setattr(curriculum_planner_mod, "run_llm", fake_run_llm)
    monkeypatch.setattr(curriculum_planner_mod, "get_node_text_model", lambda *args, **kwargs: "fast-model")
    published_events: list[object] = []
    monkeypatch.setattr(
        curriculum_planner_mod,
        "publish_runtime_event",
        lambda generation_id, event: published_events.append(event),
    )

    result = await curriculum_planner_mod.curriculum_planner(state)

    section = result["curriculum_outline"][0]
    assert section.terms_to_define == ["chlorophyll"]
    assert section.practice_target == "name the role of chlorophyll"
    assert section.visual_commitment == "diagram"
    planner_event = next(event for event in published_events if event.type == "curriculum_planned")
    assert planner_event.path == "fresh"
    assert planner_event.result == "planned"
    assert len(planner_event.duplicate_term_warnings) == 1
    assert "Duplicate term assignment in curriculum plan" in planner_event.duplicate_term_warnings[0]


def test_warn_duplicate_terms_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    sections = [
        _section_plan(section_id="s-01", terms_to_define=["chlorophyll"]),
        _section_plan(section_id="s-02", position=2, terms_to_define=["Chlorophyll"]),
    ]

    with caplog.at_level(logging.WARNING):
        warnings = curriculum_planner_mod._warn_duplicate_terms(sections, "gen-dup")

    assert "Duplicate term assignment in curriculum plan" in caplog.text
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_phased_content_generator_includes_visual_context_in_practice_prompt(monkeypatch) -> None:
    captured_prompts: dict[str, str] = {}

    async def fake_run_llm(**kwargs):
        captured_prompts[kwargs["node"]] = kwargs["user_prompt"]
        node = kwargs["node"]
        if node == "content_generator_core":
            return SimpleNamespace(
                output=CoreContent(
                    section_id="s-01",
                    template_id="guided-concept-path",
                    header=SectionHeaderContent(
                        title="Photosynthesis basics",
                        subject="Science",
                        grade_band="secondary",
                    ),
                    hook=HookHeroContent(
                        headline="Why leaves matter",
                        body="Leaves capture light energy.",
                        anchor="photosynthesis",
                    ),
                    explanation=ExplanationContent(
                        body="Plants use chlorophyll to capture light.",
                        emphasis=["chlorophyll"],
                    ),
                )
            )
        if node == "content_generator_practice":
            return SimpleNamespace(
                output=PracticePhaseContent(
                    practice=PracticeContent(
                        problems=[
                            PracticeProblem(
                                difficulty="warm",
                                question="Why would a shaded leaf make less food?",
                                hints=[PracticeHint(level=1, text="Think about light capture.")],
                            )
                        ]
                    ),
                    what_next=WhatNextContent(
                        body="Next we connect this to plant structure.",
                        next="Plant structure",
                    ),
                )
            )
        if node == "content_generator_enrichment":
            return SimpleNamespace(
                output=EnrichmentPhaseContent(
                    definition=DefinitionContent(
                        term="chlorophyll",
                        formal="A pigment that absorbs light energy in photosynthesis.",
                        plain="The green substance that helps plants capture light.",
                    )
                )
            )
        raise AssertionError(f"Unexpected node {node}")

    monkeypatch.setattr(content_generator_mod, "Agent", FakeAgent)
    monkeypatch.setattr(content_generator_mod, "run_llm", fake_run_llm)
    monkeypatch.setattr(content_generator_mod, "get_node_text_model", lambda *args, **kwargs: "standard-model")

    state = _base_state(
        current_section_plan=_section_plan(
            visual_commitment="none",
            terms_to_define=["chlorophyll"],
            practice_target="apply chlorophyll knowledge to explain light capture",
        )
    )

    result = await content_generator_mod.content_generator(state)

    assert "content_generator" in result["completed_nodes"]
    assert "This section has NO diagram or interactive" in captured_prompts["content_generator_practice"]
    assert "practice_target: apply chlorophyll knowledge to explain light capture" in captured_prompts["content_generator_practice"]
