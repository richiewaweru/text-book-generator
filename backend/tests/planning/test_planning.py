from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from planning.fallback import build_fallback_spec
from planning.models import (
    PlanningRefinementOutput,
    PlanningTemplateContract,
    StudioBriefRequest,
)
from planning.normalizer import normalize_brief
from planning.section_composer import compose_sections
from planning.service import PlanningService
from planning.template_scorer import choose_template
from planning.visual_router import route_visuals


def build_brief(**overrides) -> StudioBriefRequest:
    payload = {
        "intent": "Teach long division to Year 6 students using short worked examples and guided practice",
        "audience": "Year 6 mixed ability",
        "prior_knowledge": "Confident with multiplication facts",
        "extra_context": "",
        "signals": {
            "topic_type": None,
            "learning_outcome": None,
            "class_style": ["needs-explanation-first"],
            "format": "both",
        },
        "preferences": {
            "tone": "supportive",
            "reading_level": "simple",
            "explanation_style": "balanced",
            "example_style": "everyday",
            "brevity": "balanced",
        },
        "constraints": {
            "more_practice": False,
            "keep_short": False,
            "use_visuals": False,
            "print_first": False,
        },
    }
    payload.update(overrides)
    return StudioBriefRequest.model_validate(payload)


def build_contract(
    *,
    template_id: str = "guided-concept-path",
    name: str = "Guided Concept Path",
    intent: str = "introduce-concept",
    signal_affinity: dict | None = None,
    section_role_defaults: dict | None = None,
    available_components: list[str] | None = None,
    always_present: list[str] | None = None,
    component_budget: dict[str, int] | None = None,
    max_per_section: dict[str, int] | None = None,
    best_for: list[str] | None = None,
    tags: list[str] | None = None,
    not_ideal_for: list[str] | None = None,
) -> PlanningTemplateContract:
    return PlanningTemplateContract.model_validate(
        {
            "id": template_id,
            "name": name,
            "family": "guided-concept",
            "intent": intent,
            "tagline": "Template tagline",
            "reading_style": "linear-guided",
            "tags": tags or [],
            "best_for": best_for or [],
            "not_ideal_for": not_ideal_for or [],
            "learner_fit": ["general"],
            "subjects": ["mathematics"],
            "interaction_level": "medium",
            "always_present": always_present or ["section-header", "hook-hero", "what-next-bridge"],
            "available_components": available_components
            or [
                "hook-hero",
                "explanation-block",
                "worked-example-card",
                "practice-stack",
                "diagram-block",
                "summary-block",
                "what-next-bridge",
                "process-steps",
            ],
            "component_budget": component_budget or {"diagram-block": 1, "worked-example-card": 1},
            "max_per_section": max_per_section or {"diagram-block": 1, "worked-example-card": 1},
            "default_behaviours": {},
            "section_role_defaults": section_role_defaults
            or {
                "intro": ["hook-hero"],
                "explain": ["diagram-block", "worked-example-card", "explanation-block"],
                "practice": ["practice-stack"],
                "summary": ["summary-block", "what-next-bridge"],
            },
            "signal_affinity": signal_affinity
            or {
                "topic_type": {"concept": 0.9, "process": 0.45, "facts": 0.5, "mixed": 0.6},
                "learning_outcome": {
                    "understand-why": 0.9,
                    "be-able-to-do": 0.45,
                    "remember-terms": 0.5,
                    "apply-to-new": 0.6,
                },
                "class_style": {
                    "needs-explanation-first": 0.85,
                    "tries-before-told": 0.35,
                    "engages-with-visuals": 0.5,
                    "responds-to-worked-examples": 0.75,
                    "restless-without-activity": 0.4,
                },
                "format": {
                    "printed-booklet": 0.7,
                    "screen-based": 0.8,
                    "both": 0.78,
                },
            },
            "layout_notes": [],
            "responsive_rules": [],
            "print_rules": ["Flatten complex interaction for print."],
            "allowed_presets": ["blue-classroom"],
            "why_this_template_exists": "Planning tests",
            "generation_guidance": {
                "tone": "clear",
                "pacing": "steady",
                "chunking": "medium",
                "emphasis": "concept clarity",
                "avoid": ["overload"],
            },
        }
    )


def test_normalizer_derives_defaults_and_scope_warning():
    brief = build_brief(
        intent="How to solve long division using short worked examples for mixed-ability Year 6 students"
    )

    normalized = normalize_brief(brief)

    assert normalized.resolved_topic_type == "process"
    assert normalized.resolved_learning_outcome == "be-able-to-do"
    assert normalized.directives.scaffold_level == "high"
    assert normalized.scope_warning is not None


def test_template_scorer_uses_metadata_when_affinity_is_missing():
    process_brief = normalize_brief(
        build_brief(
            signals={
                "topic_type": "process",
                "learning_outcome": "be-able-to-do",
                "class_style": [],
                "format": "both",
            }
        )
    )
    procedure = build_contract(
        template_id="procedure",
        name="Procedure",
        intent="teach-procedure",
        signal_affinity={"topic_type": {}, "learning_outcome": {}, "class_style": {}, "format": {}},
        section_role_defaults={
            "intro": ["hook-hero"],
            "process": ["process-steps"],
            "explain": ["explanation-block"],
            "practice": ["practice-stack"],
            "summary": ["what-next-bridge"],
        },
        available_components=["hook-hero", "process-steps", "explanation-block", "practice-stack", "what-next-bridge"],
        best_for=["step-by-step procedures"],
        tags=["procedure", "method"],
    )
    concept = build_contract(template_id="guided-concept-path", intent="introduce-concept")

    chosen, decision = choose_template(process_brief, [concept, procedure])

    assert chosen.id == "procedure"
    assert decision.chosen_id == "procedure"


def test_template_scorer_falls_back_to_open_canvas_when_scores_are_weak():
    brief = normalize_brief(
        build_brief(
            intent="Teach an unusual interdisciplinary studio topic",
            signals={
                "topic_type": "mixed",
                "learning_outcome": "apply-to-new",
                "class_style": [],
                "format": "both",
            },
            preferences={
                "tone": "neutral",
                "reading_level": "advanced",
                "explanation_style": "balanced",
                "example_style": "academic",
                "brevity": "tight",
            },
        )
    )
    weak_contract = build_contract(
        template_id="compare-and-apply",
        intent="compare-ideas",
        best_for=["binary contrasts"],
        signal_affinity={
            "topic_type": {"concept": 0.2},
            "learning_outcome": {"remember-terms": 0.2},
            "class_style": {},
            "format": {"printed-booklet": 0.2},
        },
    )
    open_canvas = build_contract(
        template_id="open-canvas",
        name="Open Canvas",
        intent="introduce-concept",
        tags=["flexible", "open"],
        best_for=["broad or novel lesson shapes"],
        available_components=["hook-hero", "callout-block", "explanation-block", "summary-block"],
        section_role_defaults={
            "intro": ["hook-hero"],
            "explain": ["explanation-block"],
            "summary": ["summary-block"],
        },
        signal_affinity={
            "topic_type": {},
            "learning_outcome": {},
            "class_style": {},
            "format": {},
        },
    )

    chosen, _ = choose_template(brief, [weak_contract, open_canvas])

    assert chosen.id == "open-canvas"


def test_section_composer_respects_component_budgets_across_sections():
    contract = build_contract()
    brief = normalize_brief(
        build_brief(
            constraints={
                "more_practice": True,
                "keep_short": False,
                "use_visuals": False,
                "print_first": False,
            }
        )
    )

    sections = compose_sections(brief, contract)

    all_components = [component for section in sections for component in section.selected_components]
    assert all_components.count("diagram-block") <= 1
    assert all_components.count("worked-example-card") <= 1
    assert any(section.role == "summary" for section in sections)
    explain_sections = [section for section in sections if section.role == "explain"]
    assert explain_sections
    assert any("explanation-block" in section.selected_components for section in explain_sections)


def test_visual_router_applies_svg_override_when_print_first_is_enabled():
    contract = build_contract(
        template_id="procedure",
        intent="teach-procedure",
        section_role_defaults={
            "intro": ["hook-hero"],
            "process": ["process-steps"],
            "explain": ["diagram-block", "explanation-block"],
            "summary": ["what-next-bridge"],
        },
        available_components=["hook-hero", "process-steps", "diagram-block", "explanation-block", "what-next-bridge"],
    )
    brief = normalize_brief(
        build_brief(
            signals={
                "topic_type": "process",
                "learning_outcome": "be-able-to-do",
                "class_style": [],
                "format": "printed-booklet",
            },
            constraints={
                "more_practice": False,
                "keep_short": True,
                "use_visuals": True,
                "print_first": True,
            },
        )
    )

    routed = route_visuals(brief, contract, compose_sections(brief, contract))

    assert any(section.visual_policy and section.visual_policy.required for section in routed)
    assert all(
        section.visual_policy.mode == "svg"
        for section in routed
        if section.visual_policy and section.visual_policy.required
    )


def test_fallback_uses_contract_defaults_and_returns_reviewable_spec():
    contract = build_contract(
        section_role_defaults={
            "intro": ["hook-hero", "callout-block"],
            "explain": ["explanation-block"],
            "summary": ["summary-block", "what-next-bridge"],
        }
    )

    spec = build_fallback_spec(brief=build_brief(), contract=contract)

    assert spec.sections[0].selected_components == ["hook-hero", "callout-block"]
    assert spec.sections[1].selected_components == ["explanation-block"]
    assert spec.sections[2].selected_components == ["summary-block", "what-next-bridge"]
    assert spec.warning is not None


def test_planning_service_emits_events_and_refines_titles():
    brief = build_brief(
        intent="Teach fractions",
        signals={
            "topic_type": "concept",
            "learning_outcome": "understand-why",
            "class_style": ["needs-explanation-first"],
            "format": "both",
        },
        constraints={
            "more_practice": False,
            "keep_short": True,
            "use_visuals": False,
            "print_first": False,
        },
    )
    contract = build_contract()
    emitted: list[dict[str, object]] = []

    async def fake_emit(payload: dict[str, object]) -> None:
        emitted.append(payload)

    async def fake_run_llm_fn(**kwargs):
        assert kwargs["generation_mode"] == "shell-draft"
        return SimpleNamespace(
            output=PlanningRefinementOutput.model_validate(
                {
                    "lesson_rationale": "A teacher-facing rationale.",
                    "warning": None,
                    "sections": [
                        {
                            "title": "Start with the core idea",
                            "rationale": "Open with the main idea before moving into practice."
                        },
                        {
                            "title": "Build the explanation",
                            "rationale": "Clarify the method and its steps."
                        },
                        {
                            "title": "Close and connect forward",
                            "rationale": "Wrap up the main takeaway."
                        },
                    ],
                }
            )
        )

    class FakeAgent:
        def __init__(self, *, model, output_type, system_prompt) -> None:
            self.model = model
            self.output_type = output_type
            self.system_prompt = system_prompt

    with patch("planning.prompt_builder.Agent", FakeAgent):
        spec = PlanningService()
        result = asyncio.run(
            spec.plan(
                brief,
                contracts=[contract],
                model=object(),
                run_llm_fn=fake_run_llm_fn,
                emit=fake_emit,
                llm_generation_mode="shell-draft",
            )
        )

    assert result.sections[0].title == "Start with the core idea"
    assert emitted[0]["event"] == "template_selected"
    assert [payload["event"] for payload in emitted[1:]] == [
        "section_planned",
        "section_planned",
        "section_planned",
    ]
