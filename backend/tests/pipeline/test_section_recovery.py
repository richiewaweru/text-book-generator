from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.graph import retry_diagram
from pipeline.nodes import content_generator as content_generator_module
from pipeline.nodes import process_section as process_section_module
from pipeline.state import QCReport, StyleContext, TextbookPipelineState
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan
from pipeline.types.requests import PipelineRequest, SectionPlan
from pipeline.types.section_content import (
    DiagramContent,
    ExplanationContent,
    HookHeroContent,
    InteractionSpec,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    SimulationContent,
    WhatNextContent,
)
from pipeline.types.template_contract import (
    GenerationGuidance,
    TemplateContractSummary,
)


class DummyAgent:
    def __init__(self, *args, **kwargs) -> None:
        _ = (args, kwargs)


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
        optional_components=["definition-card", "diagram-block", "simulation-block"],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
    )
    defaults.update(overrides)
    return TemplateContractSummary(**defaults)


def _request(**overrides) -> PipelineRequest:
    defaults = dict(
        topic="Introduction to derivatives",
        subject="Mathematics",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=1,
        generation_id="gen-test",
    )
    defaults.update(overrides)
    return PipelineRequest(**defaults)


def _plan(sid: str = "s-01") -> SectionPlan:
    return SectionPlan(
        section_id=sid,
        title=f"Section {sid}",
        position=1,
        focus="Teach the core idea clearly.",
        needs_diagram=True,
    )


def _style_context() -> StyleContext:
    return StyleContext(
        preset_id="blue-classroom",
        palette="navy, sky, parchment",
        surface_style="crisp",
        density="standard",
        typography="standard",
        template_id="guided-concept-path",
        template_family="guided-concept",
        interaction_level="medium",
        grade_band="secondary",
        learner_fit="general",
    )


def _section(sid: str = "s-01") -> SectionContent:
    return SectionContent(
        section_id=sid,
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title=f"Section {sid}",
            subject="Mathematics",
            grade_band="secondary",
        ),
        hook=HookHeroContent(
            headline="Why this matters",
            body="A compelling hook body",
            anchor="derivatives",
        ),
        explanation=ExplanationContent(
            body="The explanation of the concept",
            emphasis=["key point 1", "key point 2"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="What is 2+2?",
                    hints=[PracticeHint(level=1, text="Think about it")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next we cover integrals", next="Integrals"),
    )


def _state(**overrides) -> TextbookPipelineState:
    defaults = dict(
        request=_request(),
        contract=_contract(),
        current_section_id="s-01",
        current_section_plan=_plan("s-01"),
        curriculum_outline=[_plan("s-01")],
        style_context=_style_context(),
    )
    defaults.update(overrides)
    return TextbookPipelineState(**defaults)


@pytest.mark.asyncio
async def test_content_generator_repairs_one_validation_failure(monkeypatch) -> None:
    calls: list[str] = []
    events: list[object] = []

    async def fake_run_llm(*, node: str, **kwargs):
        _ = kwargs
        calls.append(node)
        if len(calls) == 1:
            raise RuntimeError("Exceeded maximum retries (1) for output validation")
        return SimpleNamespace(output=_section("s-01"))

    monkeypatch.setattr(content_generator_module, "Agent", DummyAgent)
    monkeypatch.setattr(content_generator_module, "get_node_text_model", lambda *args, **kwargs: object())
    monkeypatch.setattr(content_generator_module, "run_llm", fake_run_llm)
    monkeypatch.setattr(content_generator_module, "publish_runtime_event", lambda generation_id, event: events.append(event))

    result = await content_generator_module.content_generator(_state())

    assert result["generated_sections"]["s-01"].section_id == "s-01"
    assert "failed_sections" not in result
    assert [event.type for event in events] == [
        "validation_repair_attempted",
        "validation_repair_succeeded",
    ]
    assert calls == ["content_generator", "content_generator_repair"]


@pytest.mark.asyncio
async def test_content_generator_persists_failed_section_after_repair_failure(monkeypatch) -> None:
    events: list[object] = []

    async def fake_run_llm(*, node: str, **kwargs):
        _ = (node, kwargs)
        raise RuntimeError("Exceeded maximum retries (1) for output validation")

    monkeypatch.setattr(content_generator_module, "Agent", DummyAgent)
    monkeypatch.setattr(content_generator_module, "get_node_text_model", lambda *args, **kwargs: object())
    monkeypatch.setattr(content_generator_module, "run_llm", fake_run_llm)
    monkeypatch.setattr(content_generator_module, "publish_runtime_event", lambda generation_id, event: events.append(event))

    result = await content_generator_module.content_generator(_state())

    assert "generated_sections" in result
    assert "s-01" not in result["generated_sections"]
    assert result["failed_sections"]["s-01"].failed_at_node == "content_generator"
    assert result["errors"][0].node == "content_generator"
    assert [event.type for event in events] == [
        "validation_repair_attempted",
        "section_failed",
    ]


@pytest.mark.asyncio
async def test_retry_diagram_skips_timeout_rerun(monkeypatch) -> None:
    captured_steps: list[str] = []

    async def fake_run_section_steps(state, *, steps, **kwargs):
        _ = (state, kwargs)
        captured_steps[:] = [name for name, _fn in steps]
        return {"completed_nodes": captured_steps}

    monkeypatch.setattr("pipeline.graph.run_section_steps", fake_run_section_steps)

    state = _state(
        generated_sections={"s-01": _section("s-01")},
        assembled_sections={"s-01": _section("s-01")},
        diagram_outcomes={"s-01": "timeout"},
    )
    result = await retry_diagram(state)

    assert captured_steps == ["section_assembler", "qc_agent"]
    assert result["completed_nodes"] == captured_steps


@pytest.mark.asyncio
async def test_process_section_runs_phases_and_merges_outputs(monkeypatch) -> None:
    section = _section("s-01")
    section_with_diagram = section.model_copy(
        update={
            "diagram": DiagramContent(
                svg_content="<svg/>",
                caption="diagram",
                alt_text="diagram",
            )
        }
    )
    interaction_spec = InteractionSpec(
        type="graph_slider",
        goal="Understand the idea",
        anchor_content={"headline": "Hook", "body": "Explain"},
        context={"subject": "Math"},
        dimensions={"difficulty": "balanced"},
        print_translation="static_diagram",
    )
    section_with_simulation = section_with_diagram.model_copy(
        update={
            "simulation": SimulationContent(
                spec=interaction_spec,
                explanation="Interactive view",
            )
        }
    )
    composition = CompositionPlan(
        diagram=DiagramPlan(enabled=True, reasoning="Needs a diagram", diagram_type="concept_map"),
        interaction=InteractionPlan(enabled=True, reasoning="Needs interaction", interaction_type="graph_slider"),
    )

    async def fake_run_section_steps(state, *, steps, **kwargs):
        _ = (state, kwargs)
        first = steps[0][0]
        if first == "content_generator":
            return {
                "generated_sections": {"s-01": section},
                "completed_nodes": ["content_generator"],
            }
        if first == "composition_planner":
            return {
                "composition_plans": {"s-01": composition},
                "completed_nodes": ["composition_planner"],
            }
        return {
            "assembled_sections": {"s-01": section_with_simulation},
            "qc_reports": {
                "s-01": QCReport(section_id="s-01", passed=True, issues=[], warnings=[])
            },
            "completed_nodes": ["section_assembler", "qc_agent"],
        }

    async def fake_parallel_phase(state, *, steps, **kwargs):
        _ = (state, steps, kwargs)
        return {
            "generated_sections": {"s-01": section_with_simulation},
            "interaction_specs": {"s-01": interaction_spec},
            "diagram_outcomes": {"s-01": "success"},
            "completed_nodes": ["diagram_generator", "interaction_generator"],
        }

    monkeypatch.setattr(process_section_module, "run_section_steps", fake_run_section_steps)
    monkeypatch.setattr(process_section_module, "_run_parallel_phase", fake_parallel_phase)

    result = await process_section_module.process_section(_state())

    assert result["composition_plans"]["s-01"].diagram.diagram_type == "concept_map"
    assert result["interaction_specs"]["s-01"].type == "graph_slider"
    assert result["diagram_outcomes"]["s-01"] == "success"
    assert result["assembled_sections"]["s-01"].simulation is not None
    assert result["qc_reports"]["s-01"].passed is True
    assert result["completed_nodes"] == [
        "content_generator",
        "composition_planner",
        "diagram_generator",
        "interaction_generator",
        "section_assembler",
        "qc_agent",
    ]
