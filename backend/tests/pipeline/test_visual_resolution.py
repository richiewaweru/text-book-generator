from __future__ import annotations

import pytest

from pipeline.contracts import get_contract
from pipeline.nodes.image_generator import image_generator
from pipeline.nodes.section_assembler import section_assembler
from pipeline.run import _build_result
from pipeline.state import PartialSectionRecord, StyleContext, TextbookPipelineState
from pipeline.storage.image_store import LocalImageStore
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan
from pipeline.types.requests import (
	GenerationMode,
	PipelineRequest,
	SectionPlan,
	SectionVisualPolicy,
)
from pipeline.types.section_content import (
	DiagramContent,
	ExplanationContent,
	HookHeroContent,
	PracticeContent,
	PracticeHint,
	PracticeProblem,
	SectionContent,
	SectionHeaderContent,
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


def _section(sid: str = "s-01", *, template_id: str, hook_svg: str | None = None) -> SectionContent:
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
			required_components=["section-header", "hook-hero", "callout-block"],
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
