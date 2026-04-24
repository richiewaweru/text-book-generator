from __future__ import annotations

import io
import os
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

from pipeline.events import ImageOutcomeEvent
from pipeline.media.types import MediaPlan, VisualFrame, VisualSlot
from pipeline.nodes.image_generator import image_generator
from pipeline.providers.gemini_image_client import (
    GeminiImageClient,
    _provider_image_config,
    get_gemini_image_client,
)
from pipeline.providers.image_client import ImageGenerationResult
from pipeline.state import StyleContext, TextbookPipelineState
from pipeline.storage.image_store import LocalImageStore
from pipeline.types.requests import (
    GenerationMode,
    PipelineRequest,
    SectionPlan,
    SectionVisualPolicy,
)
from pipeline.types.section_content import (
    ComparisonColumn,
    ComparisonGridContent,
    ComparisonRow,
    DiagramCompareContent,
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
    diagram_compare: DiagramCompareContent | None = None,
    comparison_grid: ComparisonGridContent | None = None,
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
        diagram_compare=diagram_compare,
        comparison_grid=comparison_grid,
    )


def _state(
    *,
    diagram_slot: str,
    section_plan: SectionPlan,
    section: SectionContent,
    key_concepts: list[str] | None = None,
    compare_before_label: str | None = None,
    compare_after_label: str | None = None,
    diagram_enabled: bool = True,
    diagram_mode: str = "image",
) -> TextbookPipelineState:
    sid = section.section_id
    slot_type = {
        "diagram-block": "diagram",
        "diagram-series": "diagram_series",
        "diagram-compare": "diagram_compare",
    }[diagram_slot]
    if slot_type == "diagram_series":
        labels = (
            [step.step_label for step in section.diagram_series.diagrams]
            if section.diagram_series is not None and section.diagram_series.diagrams
            else key_concepts or ["Step 1", "Step 2", "Step 3"]
        )
        target_w, target_h = (800, 600) if len(labels) <= 2 else (800, 800)
        frames = [
            VisualFrame(
                slot_id="diagram_series",
                index=index,
                label=label,
                generation_goal=f"Render series step {index + 1}.",
                target_w=target_w,
                target_h=target_h,
            )
            for index, label in enumerate(labels)
        ]
        slot = VisualSlot(
            slot_id="diagram_series",
            slot_type="diagram_series",
            required=True,
            preferred_render=diagram_mode,
            fallback_render="svg" if diagram_mode == "image" else None,
            pedagogical_intent="Show the sequence clearly.",
            caption="Sequence caption",
            frames=frames,
        )
    elif slot_type == "diagram_compare":
        before_label = compare_before_label or (
            section.diagram_compare.before_label if section.diagram_compare is not None else "Before"
        )
        after_label = compare_after_label or (
            section.diagram_compare.after_label if section.diagram_compare is not None else "After"
        )
        slot = VisualSlot(
            slot_id="diagram_compare",
            slot_type="diagram_compare",
            required=True,
            preferred_render=diagram_mode,
            fallback_render="svg" if diagram_mode == "image" else None,
            pedagogical_intent="Compare the two states.",
            caption="Compare caption",
            frames=[
                VisualFrame(
                    slot_id="diagram_compare",
                    index=0,
                    label=before_label,
                    generation_goal="Render the before state.",
                    target_w=800,
                    target_h=600,
                ),
                VisualFrame(
                    slot_id="diagram_compare",
                    index=1,
                    label=after_label,
                    generation_goal="Render the after state.",
                    target_w=800,
                    target_h=600,
                ),
            ],
        )
    else:
        slot = VisualSlot(
            slot_id="diagram",
            slot_type="diagram",
            required=True,
            preferred_render=diagram_mode,
            fallback_render="svg" if diagram_mode == "image" else None,
            pedagogical_intent="Explain the core idea clearly.",
            caption="Single diagram caption",
            frames=[
                VisualFrame(
                    slot_id="diagram",
                    index=0,
                    label=section.header.title,
                    generation_goal="Render the main diagram.",
                    target_w=1200,
                    target_h=675,
                )
            ],
        )
    return TextbookPipelineState(
        request=_request(),
        contract=_contract(diagram_slot=diagram_slot),
        current_section_id=sid,
        current_section_plan=section_plan,
        curriculum_outline=[section_plan],
        style_context=_style_context(),
        generated_sections={sid: section},
        media_plans=(
            {sid: MediaPlan(section_id=sid, slots=[slot])}
            if diagram_enabled
            else {}
        ),
    )


class FakeImageClient:
    def __init__(self):
        self.prompts: list[str] = []
        self.sizes: list[str] = []

    @staticmethod
    def _image_bytes(size: str, *, format: str) -> bytes:
        width, height = (int(part) for part in size.split("x", maxsplit=1))
        image = Image.new("RGB", (width, height), color=(240, 248, 255))
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    async def generate_image(self, *, prompt, size="1024x1024", format="png", seed=None):
        self.prompts.append(prompt)
        self.sizes.append(size)
        return ImageGenerationResult(
            bytes=self._image_bytes(size, format="PNG"),
            format="png",
            mime_type="image/png",
        )


class FailAfterFirstImageClient(FakeImageClient):
    async def generate_image(self, *, prompt, size="1024x1024", format="png", seed=None):
        self.prompts.append(prompt)
        self.sizes.append(size)
        if len(self.prompts) > 1:
            raise RuntimeError("second compare image failed")
        return ImageGenerationResult(
            bytes=self._image_bytes(size, format="PNG"),
            format="png",
            mime_type="image/png",
        )


class FakeJpegImageClient(FakeImageClient):
    async def generate_image(self, *, prompt, size="1024x1024", format="png", seed=None):
        self.prompts.append(prompt)
        self.sizes.append(size)
        return ImageGenerationResult(
            bytes=self._image_bytes(size, format="JPEG"),
            format="jpeg",
            mime_type="image/jpeg",
        )


class FailingStore(LocalImageStore):
    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        _ = (image_bytes, generation_id, section_id, filename, format)
        raise RuntimeError("upload denied")


class RecordingStore(LocalImageStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls: list[dict[str, str]] = []
        self.payloads: list[bytes] = []

    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        self.payloads.append(image_bytes)
        self.calls.append(
            {
                "generation_id": generation_id,
                "section_id": section_id,
                "filename": filename,
                "format": format,
            }
        )
        return await super().store_image(
            image_bytes,
            generation_id=generation_id,
            section_id=section_id,
            filename=filename,
            format=format,
        )


def _capture_node_logs(monkeypatch) -> list[str]:
    messages: list[str] = []

    def _record(message: str, *args, **kwargs) -> None:
        _ = kwargs
        messages.append(message % args if args else message)

    def _record_log(level: int, message: str, *args, **kwargs) -> None:
        _ = (level, kwargs)
        messages.append(message % args if args else message)

    monkeypatch.setattr("pipeline.nodes.image_generator.logger.log", _record_log)
    monkeypatch.setattr("pipeline.nodes.image_generator.logger.info", _record)
    monkeypatch.setattr("pipeline.nodes.image_generator.logger.error", _record)
    monkeypatch.setattr("pipeline.nodes.image_generator.logger.warning", _record)
    return messages


def _capture_published_events(monkeypatch) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []

    def _publish(generation_id: str, event: object) -> None:
        events.append((generation_id, event))

    monkeypatch.setattr("pipeline.nodes.image_generator.core_events.event_bus.publish", _publish)
    return events


def _image_events(events: list[tuple[str, object]]) -> list[tuple[str, ImageOutcomeEvent]]:
    return [
        (generation_id, event)
        for generation_id, event in events
        if isinstance(event, ImageOutcomeEvent)
    ]


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


@pytest.mark.parametrize("size", ["256x256", "512x512", "1024x1024"])
def test_provider_image_config_maps_current_pipeline_sizes_to_square_1k(size: str) -> None:
    config = _provider_image_config(size)  # type: ignore[arg-type]

    assert config.aspect_ratio == "1:1"
    assert config.image_size == "1K"


@pytest.mark.asyncio
async def test_gemini_image_client_omits_output_mime_type_and_uses_provider_mime() -> None:
    fake_chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(data=b"PNG", mime_type="image/png")
                        )
                    ]
                )
            )
        ]
    )

    with patch("pipeline.providers.gemini_image_client.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content_stream.return_value = [fake_chunk]
        client = GeminiImageClient(api_key="test-key")

        result = await client.generate_image(prompt="draw a dot", format="jpeg")

    config = mock_client.return_value.models.generate_content_stream.call_args.kwargs["config"]
    assert config.image_config.aspect_ratio == "1:1"
    assert config.image_config.image_size == "1K"
    assert config.image_config.output_mime_type is None
    assert result.format == "png"
    assert result.mime_type == "image/png"


@pytest.mark.asyncio
async def test_gemini_image_client_falls_back_to_requested_format_when_provider_mime_missing(
    caplog,
) -> None:
    fake_chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(data=b"JPEG", mime_type=None)
                        )
                    ]
                )
            )
        ]
    )

    with patch("pipeline.providers.gemini_image_client.genai.Client") as mock_client:
        mock_client.return_value.models.generate_content_stream.return_value = [fake_chunk]
        client = GeminiImageClient(api_key="test-key")

        with caplog.at_level("WARNING"):
            result = await client.generate_image(prompt="draw a dot", format="jpeg")

    assert result.format == "jpeg"
    assert result.mime_type == "image/jpeg"


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
    assert result["diagram_outcomes"]["s-01"] == "success"
    assert client.prompts


@pytest.mark.asyncio
async def test_image_generator_normalises_targeted_images_to_png_store_format(tmp_path) -> None:
    store = RecordingStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeJpegImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    result = await image_generator(state, _store=store, _client=client)

    section = result["generated_sections"]["s-01"]
    assert section.diagram is not None
    assert section.diagram.image_url == "http://test/images/gen-image-test/s-01/diagram.png"
    assert store.calls == [
        {
            "generation_id": "gen-image-test",
            "section_id": "s-01",
            "filename": "diagram.png",
            "format": "png",
        }
    ]


@pytest.mark.asyncio
async def test_image_generator_normalises_compact_slots_to_600_by_400(tmp_path) -> None:
    store = RecordingStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )
    sid = "s-01"
    compact_slot = state.media_plans[sid].slots[0].model_copy(
        update={
            "slot_id": "practice-0-diagram",
            "sizing": "compact",
            "block_target": "practice",
            "problem_index": 0,
            "frames": [
                state.media_plans[sid].slots[0].frames[0].model_copy(
                    update={"slot_id": "practice-0-diagram", "target_w": 600, "target_h": 400}
                )
            ],
        }
    )
    state = state.model_copy(
        update={"media_plans": {sid: MediaPlan(section_id=sid, slots=[compact_slot])}}
    )

    result = await image_generator(state, _store=store, _client=client)

    assert result["generated_sections"][sid].practice.problems[0].diagram is not None
    assert result["generated_sections"][sid].practice.problems[0].diagram.image_url == (
        "http://test/images/gen-image-test/s-01/practice-0-diagram.png"
    )
    assert client.sizes == ["1024x1024"]
    saved = Image.open(tmp_path / "gen-image-test" / sid / "practice-0-diagram.png")
    assert saved.size == (600, 400)
    assert len(store.payloads) == 1


@pytest.mark.asyncio
async def test_image_generator_keeps_full_slot_dimensions_for_section_diagram(tmp_path) -> None:
    store = RecordingStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    await image_generator(state, _store=store, _client=client)

    assert client.sizes == ["1792x1024"]
    saved = Image.open(tmp_path / "gen-image-test" / "s-01" / "diagram.png")
    assert saved.size == (1200, 675)


@pytest.mark.asyncio
async def test_image_generator_emits_success_outcome_event(tmp_path, monkeypatch) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )
    events = _capture_published_events(monkeypatch)

    result = await image_generator(state, _store=store, _client=client)

    assert result["generated_sections"]["s-01"].diagram is not None
    image_events = _image_events(events)
    assert len(image_events) == 1
    generation_id, event = image_events[0]
    assert generation_id == "gen-image-test"
    assert isinstance(event, ImageOutcomeEvent)
    assert event.outcome == "success"
    assert event.section_id == "s-01"
    assert event.error_message is None


@pytest.mark.asyncio
async def test_image_generator_emits_skipped_outcome_for_non_image_mode(tmp_path, monkeypatch) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
        diagram_mode="svg",
    )
    events = _capture_published_events(monkeypatch)

    result = await image_generator(state, _store=store, _client=client)

    assert result == {
        "completed_nodes": ["image_generator"],
        "diagram_outcomes": {"s-01": "skipped"},
    }
    image_events = _image_events(events)
    assert len(image_events) == 1
    generation_id, event = image_events[0]
    assert generation_id == "gen-image-test"
    assert isinstance(event, ImageOutcomeEvent)
    assert event.outcome == "skipped"
    assert event.section_id == "s-01"


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
    assert section.hook.image is None
    assert len(client.prompts) == 1


@pytest.mark.asyncio
async def test_image_generator_writes_compare_pair_and_preserves_compare_text(tmp_path) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-compare",
        section_plan=_plan(role="compare", intent="compare_variants"),
        section=_section(
            diagram_compare=DiagramCompareContent(
                before_svg="<svg />",
                after_svg="<svg />",
                before_label="Unbalanced forces",
                after_label="Balanced forces",
                before_details=["Net force is not zero."],
                after_details=["Net force cancels out."],
                caption="Compare the force balance in the same system.",
                alt_text="Before and after force balance comparison.",
            ),
            comparison_grid=ComparisonGridContent(
                title="Force comparison",
                columns=[
                    ComparisonColumn(id="before", title="Before push", summary="Unbalanced"),
                    ComparisonColumn(id="after", title="After push", summary="Balanced"),
                ],
                rows=[ComparisonRow(criterion="Net force", values=["Non-zero", "Zero"])],
            ),
        ),
        compare_before_label="Before push",
        compare_after_label="After push",
    )

    result = await image_generator(state, _store=store, _client=client)

    section = result["generated_sections"]["s-01"]
    assert section.diagram_compare is not None
    assert section.diagram_compare.before_image_url == (
        "http://test/images/gen-image-test/s-01/compare-before.png"
    )
    assert section.diagram_compare.after_image_url == (
        "http://test/images/gen-image-test/s-01/compare-after.png"
    )
    assert section.diagram_compare.before_label == "Before push"
    assert section.diagram_compare.after_label == "After push"
    assert section.diagram_compare.before_details == ["Net force is not zero."]
    assert section.diagram_compare.after_details == ["Net force cancels out."]
    assert section.diagram_compare.caption == "Compare the force balance in the same system."
    assert section.diagram_compare.alt_text == "Before and after force balance comparison."
    assert len(client.prompts) == 2
    assert "same subject, same viewpoint" in client.prompts[0]
    assert "'Before push'" in client.prompts[0]
    assert "'After push'" in client.prompts[1]


@pytest.mark.asyncio
async def test_image_generator_returns_recoverable_error_when_compare_pair_fails(tmp_path) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FailAfterFirstImageClient()
    state = _state(
        diagram_slot="diagram-compare",
        section_plan=_plan(role="compare", intent="compare_variants"),
        section=_section(
            diagram_compare=DiagramCompareContent(
                before_label="Before",
                after_label="After",
                caption="A compare caption",
                alt_text="A compare alt text",
            )
        ),
        compare_before_label="Before",
        compare_after_label="After",
    )

    result = await image_generator(state, _store=store, _client=client)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "error"
    assert result["errors"][0].recoverable is True
    assert "Image generation failed for frame 1" in result["errors"][0].message


@pytest.mark.asyncio
async def test_image_generator_logs_disabled_image_mode_and_records_error_outcome(
    monkeypatch,
) -> None:
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
        diagram_enabled=False,
    )

    _messages = _capture_node_logs(monkeypatch)
    events = _capture_published_events(monkeypatch)

    result = await image_generator(state)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "skipped"
    image_events = _image_events(events)
    assert len(image_events) == 1
    assert image_events[0][1].outcome == "skipped"


@pytest.mark.asyncio
async def test_image_generator_skips_svg_mode_without_overwriting_diagram_outcome(
    monkeypatch,
) -> None:
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
        diagram_mode="svg",
    )

    _messages = _capture_node_logs(monkeypatch)
    events = _capture_published_events(monkeypatch)

    result = await image_generator(state)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "skipped"
    image_events = _image_events(events)
    assert len(image_events) == 1
    assert image_events[0][1].outcome == "skipped"


@pytest.mark.asyncio
async def test_image_generator_logs_success_path(tmp_path, monkeypatch) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    messages = _capture_node_logs(monkeypatch)

    result = await image_generator(state, _store=store, _client=client)

    assert result["generated_sections"]["s-01"].diagram is not None
    assert result["diagram_outcomes"]["s-01"] == "success"
    assert not any(
        any(level in m for level in ("IMG::FAILURE", "IMG::STORE_WRITE_FAILURE", "IMG::API_FAILURE"))
        for m in messages
    )


@pytest.mark.asyncio
async def test_image_generator_returns_recoverable_error_when_api_key_missing(
    tmp_path,
    monkeypatch,
) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    monkeypatch.setattr("pipeline.nodes.image_generator.get_image_store", lambda: store)
    monkeypatch.setattr("pipeline.nodes.image_generator.resolve_gemini_image_api_key", lambda: None)
    _messages = _capture_node_logs(monkeypatch)
    events = _capture_published_events(monkeypatch)

    result = await image_generator(state)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "error"
    assert result["errors"][0].recoverable is True
    assert "Image client setup failed" in result["errors"][0].message
    image_events = _image_events(events)
    assert len(image_events) == 1
    generation_id, event = image_events[0]
    assert generation_id == "gen-image-test"
    assert isinstance(event, ImageOutcomeEvent)
    assert event.outcome == "error"
    assert "No Gemini API key found" in (event.error_message or "")


@pytest.mark.asyncio
async def test_image_generator_returns_recoverable_error_when_store_init_fails(
    monkeypatch,
) -> None:
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    def _boom():
        raise RuntimeError("bucket unavailable")

    monkeypatch.setattr("pipeline.nodes.image_generator.get_image_store", _boom)
    _messages = _capture_node_logs(monkeypatch)

    result = await image_generator(state, _client=FakeImageClient())

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "error"
    assert result["errors"][0].recoverable is True
    assert result["errors"][0].message == "Image client setup failed: bucket unavailable"


@pytest.mark.asyncio
async def test_image_generator_returns_recoverable_error_when_client_init_fails(
    tmp_path,
    monkeypatch,
) -> None:
    store = LocalImageStore(base_path=tmp_path, base_url="http://test/images")
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    monkeypatch.setattr("pipeline.nodes.image_generator.get_image_store", lambda: store)
    monkeypatch.setattr("pipeline.nodes.image_generator.resolve_gemini_image_api_key", lambda: "test-key")

    def _boom():
        raise RuntimeError("auth rejected")

    monkeypatch.setattr("pipeline.nodes.image_generator.get_image_client", _boom)
    _capture_node_logs(monkeypatch)

    result = await image_generator(state)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "error"
    assert result["errors"][0].recoverable is True
    assert result["errors"][0].message == "Image client setup failed: auth rejected"


@pytest.mark.asyncio
async def test_image_generator_returns_recoverable_error_when_store_upload_fails(
    tmp_path,
    monkeypatch,
) -> None:
    store = FailingStore(base_path=tmp_path, base_url="http://test/images")
    client = FakeImageClient()
    state = _state(
        diagram_slot="diagram-block",
        section_plan=_plan(intent="explain_structure"),
        section=_section(),
    )

    messages = _capture_node_logs(monkeypatch)

    result = await image_generator(state, _store=store, _client=client)

    assert result["completed_nodes"] == ["image_generator"]
    assert result["diagram_outcomes"]["s-01"] == "error"
    assert result["errors"][0].recoverable is True
    assert "Image storage failed for diagram: RuntimeError: upload denied" in result["errors"][0].message
    assert any("IMG::STORE_WRITE_FAILURE::" in message for message in messages)
