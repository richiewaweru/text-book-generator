from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from pipeline.nodes.image_generator import image_generator
from pipeline.providers.gemini_image_client import GeminiImageClient, get_gemini_image_client
from pipeline.providers.image_client import ImageGenerationResult
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.storage.image_store import LocalImageStore
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan
from pipeline.types.requests import (
    GenerationMode,
    PipelineRequest,
    SectionPlan,
    SectionVisualPolicy,
)
from pipeline.types.section_content import (
    DiagramSeriesContent,
    DiagramSeriesStep,
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


@contextmanager
def _env(**kwargs: str | None):
    old = {key: os.environ.get(key) for key in kwargs}
    try:
        for key, value in kwargs.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _guidance() -> GenerationGuidance:
    return GenerationGuidance(
        tone="clear",
        pacing="steady",
        chunking="medium",
        emphasis="explanation first",
        avoid=["long prose"],
    )


def _contract(*, diagram_slot: str) -> TemplateContractSummary:
    return TemplateContractSummary(
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
        optional_components=[diagram_slot],
        default_behaviours={},
        generation_guidance=_guidance(),
        best_for=[],
        not_ideal_for=[],
        learner_fit=["general"],
        subjects=["mathematics"],
        interaction_level="medium",
        allowed_presets=["blue-classroom"],
    )


def _request() -> PipelineRequest:
    return PipelineRequest(
        topic="Introduction to derivatives",
        subject="Mathematics",
        grade_band="secondary",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        learner_fit="general",
        section_count=1,
        mode=GenerationMode.BALANCED,
        generation_id="gen-image-test",
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


def _section(
    sid: str = "s-01",
    *,
    diagram_series: DiagramSeriesContent | None = None,
) -> SectionContent:
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
        diagram_series=diagram_series,
    )


def _state(
    *,
    diagram_slot: str,
    section_plan: SectionPlan,
    section: SectionContent,
    key_concepts: list[str] | None = None,
) -> TextbookPipelineState:
    sid = section.section_id
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(diagram_slot=diagram_slot),
        current_section_id=sid,
        current_section_plan=section_plan,
        curriculum_outline=[section_plan],
        style_context=_style_context(),
        generated_sections={sid: section},
        composition_plans={
            sid: CompositionPlan(
                diagram=DiagramPlan(
                    enabled=True,
                    reasoning="needs an image",
                    mode="image",
                    key_concepts=key_concepts or ["derivative", "slope"],
                    visual_guidance="Clean and classroom-safe.",
                ),
                interaction=InteractionPlan(enabled=False, reasoning="no interaction"),
            )
        },
    )


class FakeImageClient:
    def __init__(self):
        self.prompts: list[str] = []

    async def generate_image(self, *, prompt, size="1024x1024", format="png", seed=None):
        self.prompts.append(prompt)
        return ImageGenerationResult(bytes=b"PNG", format="png", mime_type="image/png")


def _plan(
    *,
    sid: str = "s-01",
    role: str = "develop",
    intent: str = "explain_structure",
) -> SectionPlan:
    return SectionPlan(
        section_id=sid,
        title=f"Section {sid}",
        position=1,
        focus="Teach the core idea clearly.",
        role=role,
        needs_diagram=True,
        visual_policy=SectionVisualPolicy(required=True, intent=intent, mode="image"),
    )


def test_gemini_image_client_uses_developer_api() -> None:
    with patch("pipeline.providers.gemini_image_client.genai.Client") as mock_client:
        GeminiImageClient(api_key="test-key")

    mock_client.assert_called_once_with(vertexai=False, api_key="test-key")


def test_get_gemini_image_client_prefers_nano_key() -> None:
    get_gemini_image_client.cache_clear()
    with _env(
        GOOGLE_CLOUD_NANO_API_KEY="nano-key",
        GOOGLE_API_KEY="google-key",
        GEMINI_API_KEY="gemini-key",
    ):
        with patch("pipeline.providers.gemini_image_client.GeminiImageClient") as mock_cls:
            get_gemini_image_client()

    mock_cls.assert_called_once_with(api_key="nano-key")
    get_gemini_image_client.cache_clear()


@pytest.mark.asyncio
async def test_image_generator_writes_single_image_with_local_store(tmp_path) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    result = await image_generator(state, _store=store, _client=client)

    section = result["generated_sections"]["s-01"]
    assert section.diagram is not None
    assert section.diagram.image_url == "http://test/images/gen-image-test/s-01/diagram.png"
    assert client.prompts


@pytest.mark.asyncio
async def test_image_generator_routes_series_images_to_diagram_series(tmp_path) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-series",
        section_plan=_plan(intent="demonstrate_process"),
        section=_section(
            diagram_series=DiagramSeriesContent(
                title="Photosynthesis sequence",
                diagrams=[
                    DiagramSeriesStep(
                        step_label="Light absorption",
                        caption="Step one caption",
                        svg_content="<svg />",
                    ),
                    DiagramSeriesStep(
                        step_label="Carbon fixation",
                        caption="Step two caption",
                        svg_content="<svg />",
                    ),
                ],
            )
        ),
        key_concepts=["Light absorption", "Carbon fixation"],
    )

    result = await image_generator(state, _store=store, _client=client)

    section = result["generated_sections"]["s-01"]
    assert section.diagram is None
    assert section.diagram_series is not None
    assert len(section.diagram_series.diagrams) == 2
    assert section.diagram_series.diagrams[0].image_url is not None
    assert section.diagram_series.diagrams[1].image_url is not None
    assert len(client.prompts) == 2


@pytest.mark.asyncio
async def test_image_generator_populates_hook_image_for_show_realism_intro(tmp_path) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(role="intro", intent="show_realism"),
        section=_section(),
    )

    result = await image_generator(state, _store=store, _client=client)

    section = result["generated_sections"]["s-01"]
    assert section.diagram is not None
    assert section.hook.image is not None
    assert section.hook.image.url == "http://test/images/gen-image-test/s-01/hook.png"
    assert len(client.prompts) == 2


@pytest.mark.asyncio
async def test_image_generator_skips_diagram_compare_slots() -> None:
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-compare",
        section_plan=_plan(role="compare", intent="compare_variants"),
        section=_section(),
    )

    result = await image_generator(state, _client=client)

    assert result == {"completed_nodes": ["image_generator"]}
    assert client.prompts == []
