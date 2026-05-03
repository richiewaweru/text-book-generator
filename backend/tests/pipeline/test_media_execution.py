from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.media.executors.simulation_generator import _parse_simulation_output
from pipeline.media.qc.simulation_qc import _check_complexity, _check_html_safety, validate_simulation_content
from pipeline.media.slot_state import pending_required_slot_ids
from pipeline.media.types import (
    MediaPlan,
    VisualFrame,
    VisualFrameResult,
    VisualFrameResultStatus,
    VisualRender,
    VisualSlot,
    VisualSlotResult,
)
from pipeline.nodes.diagram_generator import RawSvgDiagramOutput, _series_seed_steps
from pipeline.nodes.diagram_generator import diagram_generator as diagram_node
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.section_assembler import section_assembler
from pipeline.state import MediaFrameRetryRequest, StyleContext, TextbookPipelineState
from pipeline.types.section_content import (
    DiagramContent,
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    SimulationContent,
    WhatNextContent,
    WorkedExampleContent,
    WorkedStep,
)
from pipeline.types.requests import BlockVisualPlacement, GenerationMode, PipelineRequest, SectionPlan
from pipeline.types.template_contract import GenerationGuidance, TemplateContractSummary


def _guidance() -> GenerationGuidance:
    return GenerationGuidance(
        tone="clear",
        pacing="steady",
        chunking="medium",
        emphasis="explanation first",
        avoid=["long prose"],
    )


def _request() -> PipelineRequest:
    return PipelineRequest(
        subject="Mathematics",
        context="Teach rates of change",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        mode=GenerationMode.BALANCED,
        generation_id="gen-media-exec",
    )


def _contract(*, required: list[str] | None = None, optional: list[str] | None = None) -> TemplateContractSummary:
    return TemplateContractSummary(
        id="guided-concept-path",
        name="Guided Concept Path",
        family="guided-concept",
        intent="introduce-concept",
        tagline="test",
        lesson_flow=["Hook", "Explain", "Practice"],
        required_components=required
        or ["section-header", "hook-hero", "explanation-block", "practice-stack", "what-next-bridge"],
        optional_components=optional or [],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
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


def _section() -> SectionContent:
    return SectionContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(title="Rates of change", subject="Mathematics", grade_band="secondary"),
        hook=HookHeroContent(headline="Why this matters", body="A short hook.", anchor="slope"),
        explanation=ExplanationContent(
            body="Rates of change connect graphs and equations.",
            emphasis=["rates of change", "graphs", "equations"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="What changes?",
                    hints=[PracticeHint(level=1, text="Compare the values.")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next we connect this to gradients.", next="Gradients"),
    )


def _base_state(*, media_plan: MediaPlan, contract: TemplateContractSummary | None = None) -> TextbookPipelineState:
    section = _section()
    slot_types = {slot.slot_type.value for slot in media_plan.slots}
    required_components = [
        "section-header",
        "hook-hero",
        "explanation-block",
        "practice-stack",
        "what-next-bridge",
    ]
    if "diagram" in slot_types:
        required_components.append("diagram-block")
    if "simulation" in slot_types:
        required_components.append("simulation-block")
    section_plan = SectionPlan(
        section_id=section.section_id,
        title=section.header.title,
        position=1,
        focus="Make the concept visible.",
        needs_diagram=True,
        interaction_policy="required",
        required_components=required_components,
    )
    return TextbookPipelineState(
        request=_request(),
        contract=contract or _contract(optional=["diagram-block", "simulation-block"]),
        current_section_id=section.section_id,
        current_section_plan=section_plan,
        style_context=_style_context(),
        generated_sections={section.section_id: section},
        media_plans={section.section_id: media_plan},
    )


def test_pending_required_slot_ids_prefers_media_slot_results_over_stale_section_preview() -> None:
    slot = VisualSlot(
        slot_id="diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        pedagogical_intent="Explain structure.",
        caption="A planned caption.",
        frames=[VisualFrame(slot_id="diagram", index=0, label="Main", generation_goal="Show the core idea.")],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot]))
    state.generated_sections["s-01"] = state.generated_sections["s-01"].model_copy(
        update={
            "diagram": {
                "svg_content": "<svg />",
                "caption": "Old preview caption",
                "alt_text": "Old preview alt",
            }
        }
    )
    state.media_slot_results = {
        "s-01": {
            "diagram": VisualSlotResult(
                slot_id="diagram",
                slot_type="diagram",
                required=True,
                render=VisualRender.SVG,
                caption="A planned caption.",
                ready=False,
            )
        }
    }

    assert pending_required_slot_ids(state) == ["diagram"]


@pytest.mark.asyncio
async def test_section_assembler_builds_static_and_simulation_content_from_media_results() -> None:
    diagram_slot = VisualSlot(
        slot_id="diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        pedagogical_intent="Explain structure.",
        caption="A planned diagram caption.",
        frames=[VisualFrame(slot_id="diagram", index=0, label="Main", generation_goal="Show the core idea.")],
    )
    simulation_slot = VisualSlot(
        slot_id="simulation",
        slot_type="simulation",
        required=True,
        preferred_render="html_simulation",
        fallback_render="svg",
        pedagogical_intent="Let learners manipulate the idea.",
        caption="Interactive exploration.",
        frames=[VisualFrame(slot_id="simulation", index=0, label="Explore", generation_goal="Create an interactive view.")],
        simulation_intent="Explore how the graph changes.",
        simulation_type="graph_slider",
        simulation_goal="Explore how the graph changes.",
        anchor_block="explanation",
        print_translation="static_diagram",
        expects_static_fallback=True,
    )
    state = _base_state(
        media_plan=MediaPlan(section_id="s-01", slots=[diagram_slot, simulation_slot]),
        contract=_contract(optional=["diagram-block", "simulation-block"]),
    )
    state.media_frame_results = {
        "s-01": {
            "diagram": {
                "0": VisualFrameResult(
                    slot_id="diagram",
                    frame_index=0,
                    label="Main",
                    render=VisualRender.SVG,
                    status=VisualFrameResultStatus.GENERATED,
                    svg_content="<svg><rect /></svg>",
                    alt_text="Main diagram alt",
                )
            },
            "simulation": {
                "0": VisualFrameResult(
                    slot_id="simulation",
                    frame_index=0,
                    label="Explore",
                    render=VisualRender.HTML_SIMULATION,
                    status=VisualFrameResultStatus.GENERATED,
                    html_content="<!doctype html><html><body>interactive</body></html>",
                    interaction_spec={
                        "type": "graph_slider",
                        "goal": "Explore how the graph changes.",
                        "anchor_content": {"headline": "Why this matters", "body": "A short hook."},
                        "context": {
                            "learner_level": "required",
                            "template_id": "guided-concept-path",
                            "color_mode": "light",
                            "accent_color": "#17417a",
                            "surface_color": "#f7fbff",
                            "font_mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                        },
                        "dimensions": {"width": "100%", "height": 420, "resizable": True},
                        "print_translation": "static_diagram",
                    },
                    explanation="Interactive view for rates of change.",
                )
            },
        }
    }

    result = await section_assembler(state)

    assembled = result["assembled_sections"]["s-01"]
    assert assembled.diagram is not None
    assert assembled.diagram.caption == "A planned diagram caption."
    assert assembled.simulation is not None
    assert assembled.simulation.html_content is not None
    assert assembled.simulation.fallback_diagram is not None
    assert assembled.simulation.fallback_diagram.caption == "A planned diagram caption."


@pytest.mark.asyncio
async def test_simulation_generator_produces_html_and_lectio_aligned_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    simulation_slot = VisualSlot(
        slot_id="simulation",
        slot_type="simulation",
        required=True,
        preferred_render="html_simulation",
        fallback_render="svg",
        pedagogical_intent="Let learners manipulate the idea.",
        caption="Interactive exploration.",
        frames=[VisualFrame(slot_id="simulation", index=0, label="Explore", generation_goal="Create an interactive view.")],
        simulation_intent="Explore how the graph changes.",
        simulation_type="graph_slider",
        simulation_goal="Explore how the graph changes.",
        anchor_block="explanation",
        print_translation="hide",
    )
    state = _base_state(
        media_plan=MediaPlan(section_id="s-01", slots=[simulation_slot]),
        contract=_contract(optional=["simulation-block"]),
    )

    async def _run_llm(**kwargs):
        _ = kwargs
        return SimpleNamespace(
            output=(
                "<!doctype html><html><body><button>Play</button><button>Pause</button>"
                "<button>Reset</button><input type=\"range\" /></body></html>\n"
                "SIMULATION_META:\n"
                "type: timeline_scrubber\n"
                "goal: Explore how the graph changes.\n"
                "explanation: Press play to animate the changing state."
            )
        )

    monkeypatch.setattr("pipeline.media.executors.simulation_generator.get_node_text_model", lambda *args, **kwargs: object())
    monkeypatch.setattr("pipeline.media.executors.simulation_generator.Agent", lambda *args, **kwargs: object())
    monkeypatch.setattr("pipeline.media.executors.simulation_generator.run_llm", _run_llm)

    result = await interaction_generator(state)

    simulation = result["generated_sections"]["s-01"].simulation
    assert simulation is not None
    assert simulation.html_content is not None
    assert simulation.spec.context.template_id == "guided-concept-path"
    assert simulation.spec.dimensions.width == "100%"
    assert simulation.spec.dimensions.resizable is True
    assert simulation.spec.type == "timeline_scrubber"
    assert result["media_slot_results"]["s-01"]["simulation"].ready is True


def test_simulation_qc_requires_html_and_required_fallback() -> None:
    slot = VisualSlot(
        slot_id="simulation",
        slot_type="simulation",
        required=True,
        preferred_render="html_simulation",
        caption="Interactive exploration.",
        pedagogical_intent="Let learners manipulate the idea.",
        frames=[VisualFrame(slot_id="simulation", index=0, generation_goal="Create an interactive view.")],
        print_translation="static_diagram",
        expects_static_fallback=True,
    )

    issues = validate_simulation_content(
        slot=slot,
        simulation=SimulationContent(
            spec={
                "type": "graph_slider",
                "goal": "Explore the graph.",
                "anchor_content": {"headline": "Hook"},
                "context": {
                    "learner_level": "required",
                    "template_id": "guided-concept-path",
                    "color_mode": "light",
                    "accent_color": "#17417a",
                    "surface_color": "#f7fbff",
                    "font_mono": "ui-monospace",
                },
                "dimensions": {"width": "100%", "height": 420, "resizable": True},
                "print_translation": "static_diagram",
            },
            html_content="",
        ),
        fallback_diagram=None,
    )

    assert "simulation html_content is missing" in issues
    assert "simulation fallback_diagram is required for print translation" in issues


def test_parse_simulation_output_tolerates_missing_meta() -> None:
    parsed = _parse_simulation_output(
        "<!doctype html><html><body><input type=\"range\" /></body></html>",
        slot=VisualSlot(
            slot_id="simulation",
            slot_type="simulation",
            required=True,
            preferred_render="html_simulation",
            caption="Interactive exploration.",
            pedagogical_intent="Explore the concept.",
            frames=[VisualFrame(slot_id="simulation", index=0, generation_goal="Create an interactive view.")],
            simulation_goal="Explore the graph.",
        ),
    )

    assert parsed.html_content.startswith("<!doctype html>")
    assert parsed.simulation_type == "graph_slider"
    assert parsed.goal == "Explore the graph."


def test_legacy_diagram_series_seed_uses_plan_title_when_header_missing() -> None:
    section = _section().model_copy(update={"header": None})
    plan = SectionPlan(
        section_id="s-01",
        title="See Positive and Negative Slopes",
        position=1,
        focus="Show slope visually.",
        terms_to_define=["positive slope"],
    )

    steps = _series_seed_steps(section, plan)

    assert steps[0].step_label == "See Positive and Negative Slopes"
    assert steps[0].caption == (
        "See Positive and Negative Slopes - See Positive and Negative Slopes"
    )


def test_simulation_qc_flags_forbidden_patterns_and_slider_count() -> None:
    assert _check_html_safety("<script src=\"https://cdn.jsdelivr.net/lib.js\"></script>")
    assert _check_complexity(
        "<input type=\"range\" /><input type=\"range\" /><input type=\"range\" />"
        "<input type=\"range\" /><input type=\"range\" />"
    ) == ["simulation html_content uses more than four slider controls"]


@pytest.mark.asyncio
async def test_graph_visible_diagram_node_delegates_to_media_executor(monkeypatch) -> None:
    async def fake_executor(state, *, model_overrides=None, config=None):
        _ = (state, model_overrides, config)
        return {"completed_nodes": ["diagram_generator"], "marker": "delegated"}

    monkeypatch.setattr(
        "pipeline.media.executors.diagram_generator.diagram_generator",
        fake_executor,
    )

    result = await diagram_node(_base_state(media_plan=MediaPlan(section_id="s-01", slots=[])))

    assert result["marker"] == "delegated"


@pytest.mark.asyncio
async def test_diagram_generator_skips_when_resource_spec_disables_diagrams() -> None:
    slot = VisualSlot(
        slot_id="diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Slope diagrams.",
        frames=[
            VisualFrame(
                slot_id="diagram-series",
                index=0,
                label="Slope 3",
                generation_goal="Draw a coordinate grid with a line showing slope 3.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot])).model_copy(
        update={
            "request": _request().model_copy(update={"resource_type": "exit_ticket"}),
        }
    )

    result = await diagram_node(state)

    assert result["completed_nodes"] == ["diagram_generator"]
    assert result["diagram_outcomes"]["s-01"] == "skipped"


@pytest.mark.asyncio
async def test_diagram_generator_writes_raw_svg_to_diagram_series(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_RAW_SVG_DIAGRAMS", raising=False)
    slot = VisualSlot(
        slot_id="diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Slope diagrams.",
        frames=[
            VisualFrame(
                slot_id="diagram-series",
                index=0,
                label="Slope 3",
                generation_goal="Draw a coordinate grid with a line showing slope 3.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot]))

    async def fake_raw_output(*args, **kwargs):
        _ = (args, kwargs)
        return RawSvgDiagramOutput(
            svg_content=(
                '<svg viewBox="0 0 600 400">'
                '<line x1="80" y1="330" x2="520" y2="70" />'
                '<text x="110" y="120">slope 3</text>'
                "</svg>"
            ),
            caption="A line rises three units for each unit of run.",
            alt_text="Coordinate graph with a rising line labeled slope 3.",
            diagram_kind="coordinate_slope",
        )

    monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_raw_svg_output", fake_raw_output)

    result = await diagram_node(state)

    series = result["generated_sections"]["s-01"].diagram_series
    frame = result["media_frame_results"]["s-01"]["diagram-series"]["0"]
    assert series is not None
    assert series.diagrams[0].svg_content.startswith("<svg")
    assert "slope 3" in series.diagrams[0].svg_content
    assert frame.svg_generation_mode == "raw_svg"
    assert frame.model_slot == "standard"
    assert frame.diagram_kind == "coordinate_slope"
    assert frame.sanitized is True
    assert frame.intent_validated is True


@pytest.mark.asyncio
async def test_diagram_series_frame_prompt_receives_previous_step_context(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_RAW_SVG_DIAGRAMS", raising=False)
    slot = VisualSlot(
        slot_id="diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Slope diagrams.",
        frames=[
            VisualFrame(
                slot_id="diagram-series",
                index=0,
                label="Axes",
                generation_goal="Draw axes for a coordinate graph.",
            ),
            VisualFrame(
                slot_id="diagram-series",
                index=1,
                label="Line",
                generation_goal="Draw the same axes with a slope line.",
            ),
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot]))
    captured_placeholders: list[dict[str, str | None]] = []

    async def fake_raw_output(*args, **kwargs):
        frame = kwargs["frame"]
        captured_placeholders.append(dict(frame.output_placeholders))
        return RawSvgDiagramOutput(
            svg_content=(
                '<svg viewBox="0 0 600 400">'
                '<line x1="80" y1="330" x2="520" y2="70" />'
                f'<text x="110" y="120">{frame.label}</text>'
                "</svg>"
            ),
            caption=f"{frame.label} uses matching axes.",
            alt_text=f"Coordinate graph frame for {frame.label}.",
            diagram_kind="coordinate_grid",
            self_check=["uses a 0-6 axis range", "keeps labels inside the canvas"],
        )

    monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_raw_svg_output", fake_raw_output)

    await diagram_node(state)

    assert "previous_steps_context" not in captured_placeholders[0]
    previous_context = captured_placeholders[1]["previous_steps_context"]
    assert previous_context is not None
    assert "Step 1 (Axes)" in previous_context
    assert "diagram kind: coordinate_grid" in previous_context
    assert "caption: Axes uses matching axes." in previous_context
    assert "self-check: uses a 0-6 axis range; keeps labels inside the canvas" in previous_context


@pytest.mark.asyncio
async def test_diagram_retry_prompt_receives_previous_failure_feedback(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_RAW_SVG_DIAGRAMS", raising=False)
    slot = VisualSlot(
        slot_id="diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Slope diagrams.",
        frames=[
            VisualFrame(
                slot_id="diagram-series",
                index=0,
                label="Slope 3",
                generation_goal="Draw a coordinate grid with a line showing slope 3.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot]))
    state.current_media_retry = MediaFrameRetryRequest(
        section_id="s-01",
        slot_id="diagram-series",
        slot_type="diagram_series",
        frame_key="0",
        frame_index=0,
        executor_node="diagram_generator",
        reason="Retrying required media frame.",
    )
    state.media_frame_results = {
        "s-01": {
            "diagram-series": {
                "0": VisualFrameResult(
                    slot_id="diagram-series",
                    frame_index=0,
                    label="Slope 3",
                    render=VisualRender.SVG,
                    status=VisualFrameResultStatus.FAILED,
                    svg_generation_mode="raw_svg",
                    svg_failure_reason="intent",
                    error_message=(
                        "Diagram generation failed for frame 0: "
                        "Brief asks for a graph/coordinate diagram but SVG appears to be a flowchart."
                    ),
                )
            }
        }
    }
    captured_placeholders: list[dict[str, str | None]] = []

    async def fake_raw_output(*args, **kwargs):
        frame = kwargs["frame"]
        captured_placeholders.append(dict(frame.output_placeholders))
        return RawSvgDiagramOutput(
            svg_content=(
                '<svg viewBox="0 0 600 400">'
                '<line x1="80" y1="330" x2="520" y2="70" />'
                '<text x="110" y="120">slope 3</text>'
                "</svg>"
            ),
            caption="A line rises three units for each unit of run.",
            alt_text="Coordinate graph with a rising line labeled slope 3.",
            diagram_kind="coordinate_slope",
        )

    monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_raw_svg_output", fake_raw_output)

    await diagram_node(state)

    feedback = captured_placeholders[0]["previous_attempt_feedback"]
    assert feedback is not None
    assert "failure category: intent" in feedback
    assert "graph/coordinate diagram" in feedback


@pytest.mark.asyncio
async def test_diagram_generator_rejects_unsafe_raw_svg_as_recoverable_failure(monkeypatch) -> None:
    monkeypatch.delenv("PIPELINE_RAW_SVG_DIAGRAMS", raising=False)
    slot = VisualSlot(
        slot_id="diagram-series",
        slot_type="diagram_series",
        required=True,
        preferred_render="svg",
        block_target="section",
        pedagogical_intent="Show slope visually.",
        caption="Slope diagrams.",
        frames=[
            VisualFrame(
                slot_id="diagram-series",
                index=0,
                label="Slope 3",
                generation_goal="Draw a coordinate grid with a line showing slope 3.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[slot]))

    async def fake_raw_output(*args, **kwargs):
        _ = (args, kwargs)
        return RawSvgDiagramOutput(
            svg_content='<svg viewBox="0 0 600 400"><script>alert(1)</script></svg>',
            caption="Unsafe diagram.",
            alt_text="Unsafe diagram.",
            diagram_kind="coordinate_slope",
        )

    monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_raw_svg_output", fake_raw_output)

    result = await diagram_node(state)

    frame = result["media_frame_results"]["s-01"]["diagram-series"]["0"]
    assert frame.status == VisualFrameResultStatus.FAILED
    assert frame.svg_generation_mode == "raw_svg"
    assert frame.svg_failure_reason == "sanitizer"
    assert result["errors"][0].recoverable is True
    assert "banned SVG tag" in result["errors"][0].message


@pytest.mark.asyncio
async def test_section_assembler_writes_compact_practice_diagram_to_target_problem() -> None:
    practice_slot = VisualSlot(
        slot_id="practice-0-diagram",
        slot_type="diagram",
        required=True,
        preferred_render="image",
        sizing="compact",
        block_target="practice",
        problem_index=0,
        pedagogical_intent="Support the selected practice problem.",
        caption="Practice support diagram.",
        frames=[
            VisualFrame(
                slot_id="practice-0-diagram",
                index=0,
                label="Practice problem 1",
                generation_goal="Show the support diagram.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[practice_slot]))
    state.current_section_plan = state.current_section_plan.model_copy(
        update={
            "needs_diagram": False,
            "required_components": [
                "section-header",
                "hook-hero",
                "explanation-block",
                "practice-stack",
                "what-next-bridge",
            ],
            "visual_placements": [
                BlockVisualPlacement(
                    block="practice",
                    slot_type="diagram",
                    sizing="compact",
                    problem_indices=[0],
                )
            ],
        }
    )
    state.media_frame_results = {
        "s-01": {
            "practice-0-diagram": {
                "0": VisualFrameResult(
                    slot_id="practice-0-diagram",
                    frame_index=0,
                    label="Practice problem 1",
                    render=VisualRender.IMAGE,
                    status=VisualFrameResultStatus.GENERATED,
                    image_url="http://test/images/gen-media-exec/s-01/practice-0-diagram.png",
                    alt_text="Practice diagram alt",
                )
            }
        }
    }

    result = await section_assembler(state)

    assembled = result["assembled_sections"]["s-01"]
    assert isinstance(assembled.practice.problems[0].diagram, DiagramContent)
    assert assembled.practice.problems[0].diagram.image_url == (
        "http://test/images/gen-media-exec/s-01/practice-0-diagram.png"
    )
    assert assembled.diagram is None


@pytest.mark.asyncio
async def test_section_assembler_writes_compact_worked_example_diagram() -> None:
    worked_slot = VisualSlot(
        slot_id="worked-example-diagram",
        slot_type="diagram",
        required=True,
        preferred_render="svg",
        sizing="compact",
        block_target="worked_example",
        pedagogical_intent="Support the worked example.",
        caption="Worked example support diagram.",
        frames=[
            VisualFrame(
                slot_id="worked-example-diagram",
                index=0,
                label="Worked example",
                generation_goal="Show the worked example setup.",
            )
        ],
    )
    state = _base_state(media_plan=MediaPlan(section_id="s-01", slots=[worked_slot]))
    state.current_section_plan = state.current_section_plan.model_copy(
        update={
            "needs_diagram": False,
            "required_components": [
                "section-header",
                "hook-hero",
                "explanation-block",
                "practice-stack",
                "what-next-bridge",
                "worked-example-card",
            ],
            "visual_placements": [
                BlockVisualPlacement(
                    block="worked_example",
                    slot_type="diagram",
                    sizing="compact",
                )
            ],
        }
    )
    state.generated_sections["s-01"] = state.generated_sections["s-01"].model_copy(
        update={
            "worked_example": WorkedExampleContent(
                title="Find the gradient",
                setup="Plot the two points.",
                steps=[WorkedStep(label="Step 1", content="Mark the rise and run.")],
                conclusion="Compute the ratio.",
            )
        }
    )
    state.media_frame_results = {
        "s-01": {
            "worked-example-diagram": {
                "0": VisualFrameResult(
                    slot_id="worked-example-diagram",
                    frame_index=0,
                    label="Worked example",
                    render=VisualRender.SVG,
                    status=VisualFrameResultStatus.GENERATED,
                    svg_content="<svg><rect /></svg>",
                    alt_text="Worked example diagram alt",
                )
            }
        }
    }

    result = await section_assembler(state)

    assembled = result["assembled_sections"]["s-01"]
    assert assembled.worked_example is not None
    assert isinstance(assembled.worked_example.diagram, DiagramContent)
    assert assembled.worked_example.diagram.caption == "Worked example support diagram."
