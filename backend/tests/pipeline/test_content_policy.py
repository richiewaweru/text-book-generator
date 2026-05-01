from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from generation import service as generation_service
from planning import routes as planning_routes
from planning import visual_router as visual_router_mod
from planning.models import PlanningSectionPlan
from pipeline.nodes import content_generator as content_generator_mod
from pipeline.nodes import curriculum_planner as curriculum_planner_mod
from pipeline.prompts.content import (
    _section_plan_policy_block,
    _visual_context_block,
    build_content_user_prompt,
)
from pipeline.prompts.curriculum import (
    build_curriculum_enrichment_system_prompt,
    build_curriculum_system_prompt,
)
from pipeline.state import TextbookPipelineState
from pipeline.types.requests import BlockVisualPlacement, GenerationMode, PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    DefinitionContent,
    ExplanationContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
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
        optional_components=["definition-card", "diagram-block"],
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


def test_section_models_accept_payloads_without_legacy_visual_fields() -> None:
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
    assert plan.visual_placements == []
    assert planning_section.terms_to_define == []
    assert planning_section.terms_assumed == []
    assert planning_section.practice_target is None
    assert planning_section.visual_placements == []


def test_planning_to_pipeline_adapters_forward_placement_fields() -> None:
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
        visual_placements=[
            BlockVisualPlacement(
                block="explanation",
                slot_type="diagram",
                hint="Use a labeled leaf diagram.",
            )
        ],
    )

    planning_route_plan = planning_routes._pipeline_section_from_planning(
        planning_section,
        generation_mode=GenerationMode.BALANCED,
    )
    generation_service_plan = generation_service._pipeline_section_from_planning(
        planning_section,
        generation_mode=GenerationMode.BALANCED,
    )

    assert planning_route_plan.terms_to_define == ["chlorophyll"]
    assert planning_route_plan.terms_assumed == ["cell"]
    assert planning_route_plan.practice_target == "identify chlorophyll's role in absorbing light"
    assert planning_route_plan.visual_placements == planning_section.visual_placements
    assert planning_route_plan.needs_diagram is True
    assert generation_service_plan.visual_placements == planning_section.visual_placements
    assert generation_service_plan.needs_diagram is True


def test_planning_to_pipeline_adapters_derive_needs_diagram_only_from_placements() -> None:
    planning_section = PlanningSectionPlan(
        id="section-1",
        order=1,
        role="intro",
        title="Intro",
        selected_components=["diagram-block"],
        visual_policy={
            "required": True,
            "intent": "explain_structure",
            "mode": "svg",
            "goal": "Show the structure clearly.",
            "style_notes": "Use a clean diagram.",
        },
        rationale="Lead with context.",
        visual_placements=[],
    )

    planning_route_plan = planning_routes._pipeline_section_from_planning(
        planning_section,
        generation_mode=GenerationMode.BALANCED,
    )
    generation_service_plan = generation_service._pipeline_section_from_planning(
        planning_section,
        generation_mode=GenerationMode.BALANCED,
    )

    assert planning_route_plan.needs_diagram is False
    assert planning_route_plan.diagram_policy == "allowed"
    assert generation_service_plan.needs_diagram is False
    assert generation_service_plan.diagram_policy == "allowed"


def test_curriculum_prompts_no_longer_delegate_needs_diagram_to_llm() -> None:
    system_prompt = build_curriculum_system_prompt(
        template_id="guided-concept-path",
        template_name="Guided Concept Path",
        template_family="guided-concept",
    )
    enrichment_prompt = build_curriculum_enrichment_system_prompt(
        template_id="guided-concept-path",
        template_name="Guided Concept Path",
        template_family="guided-concept",
    )

    assert "needs_diagram" not in system_prompt
    assert "needs_diagram" not in enrichment_prompt


def test_policy_block_reports_visual_placement_count() -> None:
    plan = _section_plan(
        terms_to_define=["chlorophyll"],
        terms_assumed=["leaf"],
        practice_target="apply the chlorophyll definition",
        visual_placements=[
            BlockVisualPlacement(
                block="explanation",
                slot_type="diagram_series",
                hint="Sequence of light capture stages.",
            )
        ],
    )

    policy = _section_plan_policy_block(plan)

    assert "terms_to_define: chlorophyll" in policy
    assert "terms_assumed: leaf" in policy
    assert "practice_target: apply the chlorophyll definition" in policy
    assert "visual_placements: 1 placement(s)" in policy


def test_visual_context_block_for_core_without_placements_forbids_visual_references() -> None:
    visual = _visual_context_block(_section_plan())
    assert "NO diagram or visual element" in visual
    assert "Do NOT reference" in visual


def test_visual_context_block_mode2_series_gives_caption_brief_instruction() -> None:
    plan = _section_plan(
        visual_placements=[
            BlockVisualPlacement(
                block="section",
                slot_type="diagram_series",
                hint="Full-section sequence visual.",
            )
        ]
    )

    visual = _visual_context_block(plan)

    assert "IS the diagram series" in visual
    assert "caption IS the image instruction" in visual
    assert "NO diagram" not in visual
    assert "NO diagram" not in visual


@pytest.mark.parametrize(
    ("slot_type", "expected"),
    [
        ("diagram", "diagram alongside the explanation"),
        ("diagram_series", "diagram series above the explanation"),
        ("diagram_compare", "diagram series above the explanation"),
    ],
)
def test_visual_context_uses_placements_for_core_and_monolithic_prompts(
    slot_type: str,
    expected: str,
) -> None:
    plan = _section_plan(
        visual_placements=[
            BlockVisualPlacement(block="explanation", slot_type=slot_type, hint="Test placement.")
        ]
    )

    monolithic = build_content_user_prompt(
        section_plan=plan,
        subject="Science",
        context="Photosynthesis",
        grade_band="secondary",
        learner_fit="general",
        template_id="guided-concept-path",
    )
    assert expected in monolithic


def test_visual_context_block_targets_only_selected_practice_problems() -> None:
    plan = _section_plan(
        visual_placements=[
            BlockVisualPlacement(
                block="practice",
                slot_type="diagram",
                sizing="compact",
                hint="Use a compact grid diagram.",
                problem_indices=[0, 2],
            )
        ]
    )

    visual = _visual_context_block(plan)

    assert "problems 1 and 3" in visual
    assert "Only those specific problems may say 'the diagram'" in visual


def test_visual_context_block_forbids_practice_references_when_section_diagram_is_elsewhere() -> None:
    plan = _section_plan(
        visual_placements=[
            BlockVisualPlacement(block="explanation", slot_type="diagram", hint="Use a core diagram.")
        ]
    )

    visual = _visual_context_block(plan)

    assert "appears elsewhere in the section" in visual
    assert "Describe every scenario in words" in visual


def test_visual_context_block_allows_only_worked_example_visual_references_in_enrichment() -> None:
    plan = _section_plan(
        visual_placements=[
            BlockVisualPlacement(
                block="worked_example",
                slot_type="diagram",
                sizing="compact",
                hint="Use a compact worked-example diagram.",
            )
        ]
    )

    visual = _visual_context_block(plan)

    assert "worked example may include its own compact diagram" in visual
    assert "All other content must avoid visual references." in visual


@pytest.mark.asyncio
async def test_curriculum_planner_seeded_outline_passes_through_without_rerouting(monkeypatch) -> None:
    outline = [
        _section_plan(
            section_id="s-01",
            title="Intro plants",
            position=1,
            role="intro",
            required_components=["diagram-block"],
            visual_placements=[],
        ),
        _section_plan(
            section_id="s-02",
            title="Practice plants",
            position=2,
            role="process",
            required_components=["diagram-series"],
            visual_placements=[],
        ),
    ]
    state = _base_state(
        request=_request(section_plans=outline),
        current_section_plan=None,
    )
    published_events: list[object] = []
    monkeypatch.setattr(
        curriculum_planner_mod,
        "publish_runtime_event",
        lambda generation_id, event: published_events.append(event),
    )

    result = await curriculum_planner_mod.curriculum_planner(state)

    enriched = result["curriculum_outline"]
    assert enriched[0].visual_placements == []
    assert enriched[1].visual_placements == []
    assert enriched[0].required_components == ["diagram-block"]
    assert enriched[1].required_components == ["diagram-series"]
    planner_event = next(event for event in published_events if event.type == "curriculum_planned")
    assert "visual_commitment" not in planner_event.runtime_curriculum_outline[0].model_dump()
    assert planner_event.path == "seeded_passthrough"
    assert planner_event.planner_trace_sections[0].visual_placements_count == 0


@pytest.mark.asyncio
async def test_curriculum_planner_seeded_outline_reports_existing_visual_placements(monkeypatch) -> None:
    outline = [
        _section_plan(
            section_id="s-01",
            title="See plants",
            position=1,
            role="visual",
            required_components=["diagram-series"],
            visual_placements=[
                BlockVisualPlacement(
                    block="section",
                    slot_type="diagram_series",
                    hint="Full-section sequence visual.",
                )
            ],
        )
    ]
    state = _base_state(
        request=_request(section_plans=outline),
        current_section_plan=None,
    )
    published_events: list[object] = []
    monkeypatch.setattr(
        curriculum_planner_mod,
        "publish_runtime_event",
        lambda generation_id, event: published_events.append(event),
    )

    await curriculum_planner_mod.curriculum_planner(state)

    planner_event = next(event for event in published_events if event.type == "curriculum_planned")
    assert planner_event.path == "seeded_passthrough"
    assert planner_event.runtime_curriculum_outline[0].visual_placements_count == 1
    assert planner_event.planner_trace_sections[0].visual_placements_count == 1
    assert planner_event.planner_trace_sections[0].visual_placements_summary == [
        "section:diagram_series"
    ]


@pytest.mark.asyncio
async def test_curriculum_planner_rejects_request_without_section_plans() -> None:
    state = _base_state(
        request=_request(section_plans=None),
        current_section_plan=None,
        curriculum_outline=None,
    )

    result = await curriculum_planner_mod.curriculum_planner(state)

    assert result["curriculum_outline"] == []
    assert result["errors"][0].recoverable is False
    assert "No section plans provided" in result["errors"][0].message


def test_curriculum_planner_defaults_static_visual_mode_to_image() -> None:
    state = _base_state(
        request=_request(subject="History", context="Ancient trade routes"),
    )
    plan = _section_plan(
        title="Trade route map",
        focus="Show how goods moved between cities.",
    )

    mode = curriculum_planner_mod._visual_mode_for_plan(state, plan, "diagram")

    assert mode == "image"


def test_visual_router_uses_section_block_for_visual_roles() -> None:
    section = PlanningSectionPlan(
        id="section-visual",
        order=1,
        role="visual",
        title="Visual section",
        selected_components=["diagram-series"],
        rationale="Lead with the visual.",
    )

    placements = visual_router_mod._derive_visual_placements(
        section=section,
        intent="demonstrate_process",
        should_visualize=True,
    )

    assert placements[0].block == "section"
    assert placements[0].slot_type == "diagram_series"


def test_visual_router_keeps_explanation_block_for_explain_roles() -> None:
    section = PlanningSectionPlan(
        id="section-explain",
        order=1,
        role="explain",
        title="Explain section",
        selected_components=["diagram-block"],
        rationale="Support the text explanation.",
    )

    placements = visual_router_mod._derive_visual_placements(
        section=section,
        intent="explain_structure",
        should_visualize=True,
    )

    assert placements[0].block == "explanation"
    assert placements[0].slot_type == "diagram"


def test_warn_duplicate_terms_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    sections = [
        _section_plan(section_id="s-01", terms_to_define=["chlorophyll"]),
        _section_plan(section_id="s-02", position=2, terms_to_define=["Chlorophyll"]),
    ]

    with caplog.at_level(logging.WARNING):
        warnings = curriculum_planner_mod._warn_duplicate_terms(sections, "gen-dup")

    assert len(warnings) == 1
    assert "Duplicate term assignment in curriculum plan" in warnings[0]


@pytest.mark.asyncio
async def test_phased_content_generator_includes_phase_aware_visual_context_in_practice_prompt(monkeypatch) -> None:
    captured_prompts: dict[str, str] = {}

    async def fake_run_llm(**kwargs):
        captured_prompts[kwargs["node"]] = kwargs["user_prompt"]
        return SimpleNamespace(
            output=SectionContent(
                section_id="s-01",
                template_id="guided-concept-path",
                explanation=ExplanationContent(
                    body="Plants use chlorophyll to capture light.",
                    emphasis=["chlorophyll"],
                ),
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
                definition=DefinitionContent(
                    term="chlorophyll",
                    formal="A pigment that absorbs light energy in photosynthesis.",
                    plain="The green substance that helps plants capture light.",
                ),
            )
        )

    monkeypatch.setattr(content_generator_mod, "Agent", FakeAgent)
    monkeypatch.setattr(content_generator_mod, "run_llm", fake_run_llm)
    monkeypatch.setattr(content_generator_mod, "get_node_text_model", lambda *args, **kwargs: "standard-model")

    state = _base_state(
        current_section_plan=_section_plan(
            visual_placements=[
                BlockVisualPlacement(
                    block="explanation",
                    slot_type="diagram",
                    hint="Use a core diagram only.",
                )
            ],
            terms_to_define=["chlorophyll"],
            practice_target="apply chlorophyll knowledge to explain light capture",
        )
    )

    result = await content_generator_mod.content_generator(state)

    assert "content_generator" in result["completed_nodes"]
    assert "appears elsewhere in the section" in captured_prompts["content_generator"]
    assert "Describe every scenario in words" in captured_prompts["content_generator"]
    assert "practice_target: apply chlorophyll knowledge to explain light capture" in captured_prompts[
        "content_generator"
    ]
