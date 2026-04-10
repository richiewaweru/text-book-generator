from __future__ import annotations

import pytest

from pipeline.contracts import get_contract
from pipeline.nodes.diagram_generator import DiagramOutput, diagram_generator
from pipeline.nodes.image_generator import image_generator
from pipeline.nodes.section_assembler import partial_section_assembler, section_assembler
from pipeline.run import _build_result
from pipeline.state import PartialSectionRecord, PipelineError, StyleContext, TextbookPipelineState
from pipeline.storage.image_store import LocalImageStore
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan
from pipeline.types.requests import (
	GenerationMode,
	PipelineRequest,
	SectionPlan,
	SectionVisualPolicy,
)
from pipeline.types.section_content import (
	CalloutBlockContent,
	DiagramCompareContent,
	DiagramContent,
	DiagramElement,
	DiagramSeriesContent,
	DiagramSpec,
	ExplanationContent,
	HookHeroContent,
	PracticeContent,
	PracticeHint,
	PracticeProblem,
	SectionContent,
	SectionHeaderContent,
	SummaryBlockContent,
	SummaryItem,
	WhatNextContent,
)
from pipeline.types.template_contract import GenerationGuidance, TemplateContractSummary
from pipeline.visual_resolution import pending_visual_fields, resolve_visual_targets


def _request(*, template_id: str, generation_id: str = "gen-visual-test", section_count: int = 1) -> PipelineRequest:
	return PipelineRequest(
		subject="Slopes on a graph",
		context="Teach slope clearly",
		grade_band="secondary",
		template_id=template_id,
		preset_id="blue-classroom",
		learner_fit="general",
		section_count=section_count,
		mode=GenerationMode.DRAFT,
		generation_id=generation_id,
	)


def _style_context(*, template_id: str, template_family: str) -> StyleContext:
	return StyleContext(
		preset_id="blue-classroom",
		palette="navy, sky, parchment",
		surface_style="crisp",
		density="standard",
		typography="standard",
		template_id=template_id,
		template_family=template_family,
		interaction_level="medium",
		grade_band="secondary",
		learner_fit="general",
	)


def _section(
	sid: str = "s-01",
	*,
	template_id: str,
	hook_svg: str | None = None,
	callout: CalloutBlockContent | None = None,
	diagram: DiagramContent | None = None,
	diagram_series: DiagramSeriesContent | None = None,
	diagram_compare: DiagramCompareContent | None = None,
	summary: SummaryBlockContent | None = None,
) -> SectionContent:
	return SectionContent(
		section_id=sid,
		template_id=template_id,
		header=SectionHeaderContent(
			title="Test Section",
			subject="Mathematics",
			grade_band="secondary",
		),
		hook=HookHeroContent(
			headline="Why this matters",
			body="A compelling hook body.",
			anchor="slope",
			svg_content=hook_svg,
		),
		explanation=ExplanationContent(
			body="Slope describes steepness and direction.",
			emphasis=["slope is rise over run"],
		),
		practice=PracticeContent(
			problems=[
				PracticeProblem(
					difficulty="warm",
					question="What is slope?",
					hints=[PracticeHint(level=1, text="Think rise over run.")],
				),
				PracticeProblem(
					difficulty="medium",
					question="Which line is steeper?",
					hints=[PracticeHint(level=1, text="Compare the rise over run values.")],
				),
			]
		),
		what_next=WhatNextContent(body="Next we connect slope to equations.", next="y = mx + c"),
		callout=callout,
		diagram=diagram,
		diagram_series=diagram_series,
		diagram_compare=diagram_compare,
		summary=summary,
	)


def _diagram_led_plan(*, sid: str, role: str, targets: list[str], mode: str | None = None) -> SectionPlan:
	return SectionPlan(
		section_id=sid,
		title=f"Section {sid}",
		position=1,
		focus="Teach the idea visually.",
		role=role,  # type: ignore[arg-type]
		needs_diagram=True,
		required_components=["section-header", "what-next-bridge", *targets],
		visual_policy=SectionVisualPolicy(required=True, intent="explain_structure", mode=mode),  # type: ignore[arg-type]
	)


def _custom_guidance() -> GenerationGuidance:
	return GenerationGuidance(
		tone="clear",
		pacing="steady",
		chunking="medium",
		emphasis="explanation first",
		avoid=["long prose"],
	)


def _no_visual_contract() -> TemplateContractSummary:
	return TemplateContractSummary(
		id="text-only-test",
		name="Text Only Test",
		family="guided-concept",
		intent="introduce-concept",
		tagline="test",
		lesson_flow=["Hook", "Explain", "Practice"],
		required_components=["section-header", "hook-hero", "explanation-block", "practice-stack", "what-next-bridge"],
		optional_components=[],
		default_behaviours={},
		generation_guidance=_custom_guidance(),
		best_for=[],
		not_ideal_for=[],
		learner_fit=["general"],
		subjects=["mathematics"],
		interaction_level="medium",
		allowed_presets=["blue-classroom"],
	)


class _FakeImageClient:
	async def generate_image(self, *, prompt, size="1024x1024", format="png", seed=None):
		_ = (prompt, size, format, seed)
		from pipeline.providers.image_client import ImageGenerationResult

		return ImageGenerationResult(bytes=b"PNG", format="png", mime_type="image/png")


def _fake_diagram_output(title: str) -> DiagramOutput:
	return DiagramOutput(
		spec=DiagramSpec(
			type="process-flow",
			title=title,
			elements=[
				DiagramElement(id="start", label="Start", x=90, y=140, width=140, height=64),
				DiagramElement(id="next", label="Next step", x=350, y=140, width=140, height=64),
			],
			connections=[{"from_id": "start", "to_id": "next", "style": "arrow"}],
			layout_hint="horizontal",
		),
		caption=f"{title} caption",
		alt_text=f"{title} alt text",
	)


def test_diagram_led_resolves_expected_visual_targets() -> None:
	contract = get_contract("diagram-led")

	intro_state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id="intro",
		current_section_plan=_diagram_led_plan(sid="intro", role="intro", targets=["diagram-block"]),
		generated_sections={"intro": _section("intro", template_id="diagram-led")},
	)
	visual_state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id="visual",
		current_section_plan=_diagram_led_plan(
			sid="visual",
			role="visual",
			targets=["diagram-block", "diagram-series"],
		),
		generated_sections={"visual": _section("visual", template_id="diagram-led")},
	)
	summary_state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id="summary",
		current_section_plan=_diagram_led_plan(sid="summary", role="summary", targets=["diagram-block"]),
		generated_sections={"summary": _section("summary", template_id="diagram-led")},
	)

	assert resolve_visual_targets(intro_state) == ["diagram"]
	assert resolve_visual_targets(visual_state) == ["diagram", "diagram_series"]
	assert resolve_visual_targets(summary_state) == ["diagram"]


@pytest.mark.asyncio
async def test_partial_assembler_keeps_callout_sections_pending_when_only_visuals_are_missing() -> None:
	contract = get_contract("diagram-led")
	sid = "visual"
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="visual",
			targets=["diagram-block", "diagram-series", "callout-block"],
			mode="svg",
		),
		generated_sections={
			sid: _section(
				sid,
				template_id="diagram-led",
				callout=CalloutBlockContent(
					variant="remember",
					heading="Watch the sign",
					body="A negative slope can still be steep.",
				),
			)
		},
	)

	result = await partial_section_assembler(state)

	assert "errors" not in result
	assert result["partial_sections"][sid].status == "awaiting_assets"
	assert result["partial_sections"][sid].pending_assets == ["diagram", "diagram_series"]


@pytest.mark.asyncio
async def test_partial_assembler_keeps_summary_sections_pending_when_only_visuals_are_missing() -> None:
	contract = get_contract("diagram-led")
	sid = "summary"
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="summary",
			targets=["diagram-block", "summary-block"],
			mode="svg",
		),
		generated_sections={
			sid: _section(
				sid,
				template_id="diagram-led",
				summary=SummaryBlockContent(
					heading="In summary",
					items=[
						SummaryItem(text="Slope measures steepness."),
						SummaryItem(text="The sign tells you direction."),
					],
					closing="Next we connect slope to straight-line equations.",
				),
			)
		},
	)

	result = await partial_section_assembler(state)

	assert "errors" not in result
	assert result["partial_sections"][sid].status == "awaiting_assets"
	assert result["partial_sections"][sid].pending_assets == ["diagram"]


@pytest.mark.asyncio
async def test_guided_concept_path_hook_svg_satisfies_visual_requirement_without_diagram() -> None:
	contract = get_contract("guided-concept-path")
	section = _section("s-01", template_id="guided-concept-path", hook_svg="<svg><rect /></svg>")
	state = TextbookPipelineState(
		request=_request(template_id="guided-concept-path"),
		contract=contract,
		current_section_id="s-01",
		current_section_plan=SectionPlan(
			section_id="s-01",
			title="Start with the central idea",
			position=1,
			focus="Frame the lesson",
			role="intro",
			visual_policy=SectionVisualPolicy(required=True, intent="explain_structure", mode="svg"),
			required_components=["section-header", "hook-hero", "explanation-block", "what-next-bridge"],
		),
		generated_sections={"s-01": section},
	)

	assert pending_visual_fields(state) == []

	result = await section_assembler(state)

	assert "errors" not in result
	assert result["assembled_sections"]["s-01"].hook.svg_content == "<svg><rect /></svg>"


def test_build_result_marks_incomplete_runs_as_partial() -> None:
	contract = get_contract("guided-concept-path")
	plan = SectionPlan(
		section_id="s-01",
		title="Start with the central idea",
		position=1,
		focus="Frame the lesson",
		role="intro",
		visual_policy=SectionVisualPolicy(required=True, intent="explain_structure", mode="svg"),
	)
	state = TextbookPipelineState(
		request=_request(template_id="guided-concept-path", section_count=2),
		contract=contract,
		curriculum_outline=[
			plan,
			plan.model_copy(update={"section_id": "s-02", "title": "Build the explanation", "position": 2}),
		],
		partial_sections={
			"s-01": PartialSectionRecord(
				section_id="s-01",
				template_id="guided-concept-path",
				content=_section("s-01", template_id="guided-concept-path"),
				status="awaiting_assets",
				pending_assets=["diagram"],
				updated_at="2026-04-09T00:00:00+00:00",
			)
		},
		section_pending_assets={"s-01": ["diagram"]},
		section_lifecycle={"s-01": "awaiting_assets"},
	)

	result = _build_result(state.request, state.model_dump(), generation_time_seconds=12.0)

	assert result.document.status == "partial"
	assert result.document.quality_passed is False
	assert result.document.error is not None
	assert result.document.sections == []
	assert len(result.document.partial_sections) == 1


def test_build_result_marks_unusable_runs_as_failed() -> None:
	contract = get_contract("guided-concept-path")
	plan = SectionPlan(
		section_id="s-01",
		title="Start with the central idea",
		position=1,
		focus="Frame the lesson",
		role="intro",
		visual_policy=SectionVisualPolicy(required=True, intent="explain_structure", mode="svg"),
	)
	state = TextbookPipelineState(
		request=_request(template_id="guided-concept-path", section_count=1),
		contract=contract,
		curriculum_outline=[plan],
		errors=[
			PipelineError(
				node="diagram_generator",
				section_id="s-01",
				message="Diagram generation failed",
				recoverable=True,
			)
		],
		failed_sections={
			"s-01": {
				"section_id": "s-01",
				"title": "Start with the central idea",
				"position": 1,
				"failed_at_node": "diagram_generator",
				"error_type": "generation_failed",
				"error_summary": "Diagram generation failed",
				"failure_detail": {
					"node": "diagram_generator",
					"section_id": "s-01",
					"timestamp": "2026-04-09T00:00:00+00:00",
					"error_type": "generation_failed",
					"error_message": "Diagram generation failed",
				},
			}
		},
	)

	result = _build_result(state.request, state.model_dump(), generation_time_seconds=12.0)

	assert result.document.status == "failed"
	assert result.document.quality_passed is False
	assert result.document.error is not None
	assert result.document.sections == []
	assert result.document.partial_sections == []


@pytest.mark.asyncio
async def test_svg_diagram_series_writes_step_svgs_and_finalizes(monkeypatch) -> None:
	contract = get_contract("diagram-led")
	sid = "s-01"
	section = _section(
		sid,
		template_id="diagram-led",
	)
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="visual",
			targets=["diagram-series"],
			mode="svg",
		),
		style_context=_style_context(template_id="diagram-led", template_family="diagram-led"),
		generated_sections={sid: section},
		composition_plans={
			sid: CompositionPlan(
				diagram=DiagramPlan(
					enabled=True,
					reasoning="needs SVG series",
					mode="svg",
					required_targets=["diagram_series"],
					key_concepts=["First stage", "Second stage"],
					visual_guidance="Show the stages clearly.",
				),
				interaction=InteractionPlan(enabled=False, reasoning="no interaction"),
			)
		},
	)

	call_count = 0

	async def fake_generate_output(*args, **kwargs):
		nonlocal call_count
		call_count += 1
		return _fake_diagram_output(f"Series {call_count}")

	monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_diagram_output", fake_generate_output)

	result = await diagram_generator(state)
	updated_section = result["generated_sections"][sid]

	assert "errors" not in result
	assert updated_section.diagram_series is not None
	assert len(updated_section.diagram_series.diagrams) == 3
	assert all(step.svg_content.startswith("<svg") for step in updated_section.diagram_series.diagrams)

	updated_state = state.model_copy(update={"generated_sections": {sid: updated_section}})
	assert pending_visual_fields(updated_state) == []

	assembled = await section_assembler(updated_state)
	assert "errors" not in assembled
	assert assembled["assembled_sections"][sid].diagram_series is not None


@pytest.mark.asyncio
async def test_svg_diagram_compare_writes_before_and_after_svgs_and_finalizes(monkeypatch) -> None:
	contract = get_contract("diagram-led")
	sid = "s-01"
	section = _section(
		sid,
		template_id="diagram-led",
		diagram_compare=DiagramCompareContent(
			before_label="Before",
			after_label="After",
			caption="Compare the two states.",
			alt_text="Before and after comparison.",
		),
	)
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="visual",
			targets=["diagram-compare"],
			mode="svg",
		),
		style_context=_style_context(template_id="diagram-led", template_family="diagram-led"),
		generated_sections={sid: section},
		composition_plans={
			sid: CompositionPlan(
				diagram=DiagramPlan(
					enabled=True,
					reasoning="needs SVG compare",
					mode="svg",
					required_targets=["diagram_compare"],
					compare_before_label="Before",
					compare_after_label="After",
					key_concepts=["Change over time"],
					visual_guidance="Keep the compare states visually aligned.",
				),
				interaction=InteractionPlan(enabled=False, reasoning="no interaction"),
			)
		},
	)

	call_count = 0

	async def fake_generate_output(*args, **kwargs):
		nonlocal call_count
		call_count += 1
		return _fake_diagram_output(f"Compare {call_count}")

	monkeypatch.setattr("pipeline.nodes.diagram_generator._generate_diagram_output", fake_generate_output)

	result = await diagram_generator(state)
	updated_section = result["generated_sections"][sid]

	assert "errors" not in result
	assert updated_section.diagram_compare is not None
	assert updated_section.diagram_compare.before_svg.startswith("<svg")
	assert updated_section.diagram_compare.after_svg.startswith("<svg")

	updated_state = state.model_copy(update={"generated_sections": {sid: updated_section}})
	assert pending_visual_fields(updated_state) == []

	assembled = await section_assembler(updated_state)
	assert "errors" not in assembled
	assert assembled["assembled_sections"][sid].diagram_compare is not None


@pytest.mark.asyncio
async def test_image_generator_force_logs_failures_to_console(tmp_path, monkeypatch, capsys) -> None:
	store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
	contract = get_contract("diagram-led")
	sid = "s-01"
	section = _section(sid, template_id="diagram-led")
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="intro",
			targets=["diagram-block"],
			mode="image",
		),
		style_context=_style_context(template_id="diagram-led", template_family="diagram-led"),
		generated_sections={sid: section},
		composition_plans={
			sid: CompositionPlan(
				diagram=DiagramPlan(
					enabled=True,
					reasoning="needs image",
					mode="image",
					required_targets=["diagram"],
					visual_guidance="Use a clean image.",
				),
				interaction=InteractionPlan(enabled=False, reasoning="no interaction"),
			)
		},
	)

	monkeypatch.setattr("pipeline.nodes.image_generator.get_image_store", lambda: store)
	monkeypatch.setattr("pipeline.nodes.image_generator.resolve_gemini_image_api_key", lambda: None)

	result = await image_generator(state)

	captured = capsys.readouterr().err

	assert result["errors"][0].recoverable is True
	assert "IMGGEN_AI::FAIL" in captured
	assert '"reason": "no_api_key"' in captured


@pytest.mark.asyncio
async def test_section_assembler_force_logs_visual_resolution_failures(capsys) -> None:
	sid = "s-01"
	state = TextbookPipelineState(
		request=_request(template_id="text-only-test"),
		contract=_no_visual_contract(),
		current_section_id=sid,
		current_section_plan=SectionPlan(
			section_id=sid,
			title="Text only section",
			position=1,
			focus="Explain the idea.",
			role="intro",
			needs_diagram=True,
			visual_policy=SectionVisualPolicy(required=True, intent="explain_structure", mode="svg"),
		),
		generated_sections={sid: _section(sid, template_id="text-only-test")},
	)

	result = await section_assembler(state)

	captured = capsys.readouterr().err

	assert result["errors"][0].message.startswith("No supported visual target could be resolved")
	assert "FINALIZE::VISUAL_ISSUE" in captured


@pytest.mark.asyncio
async def test_image_mode_only_clears_pending_after_canonical_writeback(tmp_path) -> None:
	store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
	contract = get_contract("diagram-led")
	sid = "s-01"
	section = _section(sid, template_id="diagram-led")
	state = TextbookPipelineState(
		request=_request(template_id="diagram-led"),
		contract=contract,
		current_section_id=sid,
		current_section_plan=_diagram_led_plan(
			sid=sid,
			role="intro",
			targets=["diagram-block"],
			mode="image",
		),
		style_context=_style_context(template_id="diagram-led", template_family="diagram-led"),
		generated_sections={sid: section},
		composition_plans={
			sid: CompositionPlan(
				diagram=DiagramPlan(
					enabled=True,
					reasoning="needs image",
					mode="image",
					required_targets=["diagram"],
					visual_guidance="Use a clean image.",
				),
				interaction=InteractionPlan(enabled=False, reasoning="no interaction"),
			)
		},
	)

	result = await image_generator(state, _store=store, _client=_FakeImageClient())
	updated_section = result["generated_sections"][sid]

	assert "errors" not in result
	assert updated_section.diagram is not None
	assert updated_section.diagram.image_url is not None
	assert DiagramContent.model_validate(updated_section.diagram).image_url is not None
