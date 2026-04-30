from __future__ import annotations

import pytest

from pipeline.events import SlotRenderModeResolvedEvent
from pipeline.media.types import MediaPlan, VisualFrame, VisualRender, VisualSlot
from pipeline.nodes.media_planner import media_planner
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.types.requests import (
    BlockVisualPlacement,
    GenerationMode,
    PipelineRequest,
    SectionPlan,
)
from pipeline.types.section_content import (
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


def _guidance() -> GenerationGuidance:
    return GenerationGuidance(
        tone="clear",
        pacing="steady",
        chunking="medium",
        emphasis="explanation first",
        avoid=["long prose"],
    )


def _state() -> TextbookPipelineState:
    section = SectionContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(title="Rates of change", subject="Mathematics", grade_band="secondary"),
        hook=HookHeroContent(headline="Why this matters", body="Hook body", anchor="rates"),
        explanation=ExplanationContent(body="Explain slope with a coordinate grid and tangent line.", emphasis=["slope"]),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="What is slope?",
                    hints=[PracticeHint(level=1, text="Think about rise over run.")],
                )
            ]
        ),
        what_next=WhatNextContent(body="Next", next="More graphs"),
    )
    return TextbookPipelineState(
        request=PipelineRequest(
            topic="Rates of change",
            subject="Mathematics",
            grade_band="secondary",
            template_id="guided-concept-path",
            preset_id="blue-classroom",
            learner_fit="general",
            section_count=1,
            mode=GenerationMode.BALANCED,
            generation_id="gen-media-plan",
        ),
        contract=TemplateContractSummary(
            id="guided-concept-path",
            name="Guided Concept Path",
            family="guided-concept",
            intent="introduce-concept",
            tagline="test",
            lesson_flow=["Hook", "Explain", "Practice"],
            required_components=["section-header", "hook-hero", "explanation-block", "practice-stack", "what-next-bridge"],
            optional_components=["diagram-block"],
            default_behaviours={},
            generation_guidance=_guidance(),
            best_for=[],
            not_ideal_for=[],
            learner_fit=["general"],
            subjects=["mathematics"],
            interaction_level="medium",
            allowed_presets=["blue-classroom"],
        ),
        current_section_id=section.section_id,
        current_section_plan=SectionPlan(
            section_id="s-01",
            title="Rates of change",
            position=1,
            focus="Explain slope.",
            visual_placements=[
                BlockVisualPlacement(
                    block="explanation",
                    slot_type="diagram",
                    hint="Show the tangent line and coordinate plane.",
                )
            ],
        ),
        style_context=StyleContext(
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
        ),
        generated_sections={section.section_id: section},
    )


@pytest.mark.asyncio
async def test_media_planner_resolves_render_mode_before_parallel_generation(monkeypatch) -> None:
    published: list[tuple[str, object]] = []

    async def _build_prompt(**kwargs):
        _ = kwargs
        return "Use a precise coordinate grid with labeled axes and a tangent line.", VisualRender.SVG

    monkeypatch.setattr("pipeline.nodes.media_planner.build_intelligent_image_prompt", _build_prompt)
    monkeypatch.setattr(
        "pipeline.nodes.media_planner.event_bus.publish",
        lambda generation_id, event: published.append((generation_id, event)),
    )
    result = await media_planner(_state())

    slot = result["media_plans"]["s-01"].slots[0]
    assert slot.preferred_render == VisualRender.IMAGE
    assert slot.generation_prompt == "Use a precise coordinate grid with labeled axes and a tangent line."
    assert slot.frames[0].output_placeholders == {"image_url": None}
    assert published[0][0] == "gen-media-plan"
    assert isinstance(published[0][1], SlotRenderModeResolvedEvent)
    assert published[0][1].render_mode == "image"


@pytest.mark.asyncio
async def test_media_planner_skips_intelligent_prompt_when_content_brief_missing(monkeypatch) -> None:
    calls = 0

    async def _build_prompt(**kwargs):
        nonlocal calls
        calls += 1
        _ = kwargs
        return "unused", VisualRender.IMAGE

    monkeypatch.setattr("pipeline.nodes.media_planner.build_intelligent_image_prompt", _build_prompt)
    monkeypatch.setattr(
        "pipeline.nodes.media_planner.build_media_plan",
        lambda **kwargs: MediaPlan(
            section_id="s-01",
            slots=[
                VisualSlot(
                    slot_id="diagram",
                    slot_type="diagram",
                    required=True,
                    preferred_render="image",
                    pedagogical_intent="Explain the core idea.",
                    caption="Diagram caption.",
                    content_brief=None,
                    frames=[VisualFrame(slot_id="diagram", index=0, generation_goal="Render the main diagram.")],
                )
            ],
        ),
    )

    result = await media_planner(_state())

    assert calls == 0
    assert result["media_plans"]["s-01"].slots[0].generation_prompt is None
