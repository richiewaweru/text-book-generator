from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from core.events import event_bus
from pipeline.api import PipelineDocument, PipelineSectionReport
from pipeline.events import (
    CurriculumPlannedEvent,
    DiagramOutcomeEvent,
    FieldRegenOutcomeEvent,
    ImageOutcomeEvent,
    VisualPlacementsCommittedEvent,
    MediaPlanReadyEvent,
    MediaSlotFailedEvent,
    MediaSlotReadyEvent,
    InteractionOutcomeEvent,
    InteractionRetryQueuedEvent,
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    NodeFinishedEvent,
    NodeStartedEvent,
    PipelineStartEvent,
    SimulationTypeSelectedEvent,
    SlotRenderModeResolvedEvent,
    SectionAttemptStartedEvent,
    SectionFailedEvent,
    SectionReadyEvent,
    SectionReportUpdatedEvent,
    SectionRetryQueuedEvent,
    SectionStartedEvent,
    SectionMediaBlockedEvent,
    ValidationRepairAttemptedEvent,
    ValidationRepairSucceededEvent,
)
from pipeline.types.section_content import (
    ExplanationContent,
    HookHeroContent,
    PracticeContent,
    PracticeHint,
    PracticeProblem,
    SectionContent,
    SectionHeaderContent,
    StudentTextboxContent,
    WhatNextContent,
)
from telemetry.dtos import GenerationReport
from telemetry.services.generation_report_recorder import GenerationReportRecorder
from generation.entities.generation import Generation


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generation(generation_id: str = "gen-report") -> Generation:
    return Generation(
        id=generation_id,
        user_id="user-1",
        subject="Calculus",
        context="Explain limits",
        requested_template_id="guided-concept-path",
        requested_preset_id="blue-classroom",
        section_count=2,
        created_at=_now(),
    )


def _section(section_id: str) -> SectionContent:
    return SectionContent(
        section_id=section_id,
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title=f"Section {section_id}",
            subject="Calculus",
            grade_band="secondary",
        ),
        hook=HookHeroContent(
            headline="Hook",
            body="A short hook body for the section.",
            anchor="limits",
        ),
        explanation=ExplanationContent(
            body="A clean explanation of nearby behavior.",
            emphasis=["nearby behavior"],
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="Warm question?",
                    hints=[PracticeHint(level=1, text="Hint")],
                ),
                PracticeProblem(
                    difficulty="medium",
                    question="Medium question?",
                    hints=[PracticeHint(level=1, text="Hint")],
                ),
            ]
        ),
        what_next=WhatNextContent(
            body="Next up is continuity.",
            next="Continuity",
        ),
    )


def _document(generation_id: str, sections: list[SectionContent]) -> PipelineDocument:
    return PipelineDocument(
        generation_id=generation_id,
        subject="Calculus",
        context="Explain limits",
        template_id="guided-concept-path",
        preset_id="blue-classroom",
        status="completed",
        section_manifest=[
            {
                "section_id": section.section_id,
                "title": section.header.title,
                "position": index + 1,
            }
            for index, section in enumerate(sections)
        ],
        sections=sections,
        qc_reports=[],
        quality_passed=True,
        created_at=_now(),
        updated_at=_now(),
        completed_at=_now(),
    )


class InMemoryReportRepo:
    def __init__(self) -> None:
        self.store: dict[str, GenerationReport] = {}

    async def save_report(self, report: GenerationReport) -> str:
        self.store[report.generation_id] = report.model_copy(deep=True)
        return f"memory://report/{report.generation_id}"

    async def load_report(self, generation_id: str) -> GenerationReport:
        return self.store[generation_id]

    async def cleanup_tmp(self, generation_id: str) -> None:
        _ = generation_id


@pytest.mark.asyncio
async def test_recorder_marks_full_success_with_delivered_components() -> None:
    generation = _generation("gen-full")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        PipelineStartEvent(
            generation_id=generation.id,
            section_count=1,
            template_id="guided-concept-path",
            preset_id="blue-classroom",
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="First section",
            position=1,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.apply_event(
        SectionReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            section=_section("s-01"),
            completed_sections=1,
            total_sections=1,
        )
    )
    await recorder.finalize_success(
        document=_document(generation.id, [_section("s-01")]),
        generation_time_seconds=12.5,
    )

    report = await repo.load_report(generation.id)
    assert report.status == "completed"
    assert report.outcome == "full"
    assert report.summary.ready_sections == 1
    assert "hook" in report.sections[0].delivered_components
    assert report.generation_time_seconds == 12.5


@pytest.mark.asyncio
async def test_recorder_marks_partial_completion_with_failed_missing_section() -> None:
    generation = _generation("gen-partial")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="First section",
            position=1,
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            title="Second section",
            position=2,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.apply_event(
        SectionReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            section=_section("s-01"),
            completed_sections=1,
            total_sections=2,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.apply_event(
        NodeFinishedEvent(
            generation_id=generation.id,
            node="content_generator",
            section_id="s-02",
            attempt=1,
            status="failed",
            latency_ms=4200.0,
            error="Provider timeout",
        )
    )
    document = _document(generation.id, [_section("s-01")]).model_copy(
        update={
            "section_manifest": [
                {"section_id": "s-01", "title": "First section", "position": 1},
                {"section_id": "s-02", "title": "Second section", "position": 2},
            ]
        }
    )
    await recorder.finalize_success(document=document, generation_time_seconds=20.0)

    report = await repo.load_report(generation.id)
    assert report.outcome == "partial"
    assert report.summary.ready_sections == 1
    assert report.summary.failed_sections == 1
    assert any(section.section_id == "s-02" and section.status == "failed" for section in report.sections)


@pytest.mark.asyncio
async def test_recorder_tracks_llm_retries_and_qc_rerenders() -> None:
    generation = _generation("gen-retries")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Retry section",
            position=1,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.apply_event(
        NodeStartedEvent(
            generation_id=generation.id,
            node="content_generator",
            section_id="s-01",
            attempt=1,
        )
    )
    await recorder.apply_event(
        LLMCallStartedEvent(
            generation_id=generation.id,
            node="content_generator",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
            section_id="s-01",
        )
    )
    await recorder.apply_event(
        LLMCallFailedEvent(
            generation_id=generation.id,
            node="content_generator",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=1,
            section_id="s-01",
            latency_ms=3200.0,
            retryable=True,
            error="429 rate limit",
        )
    )
    await recorder.apply_event(
        LLMCallStartedEvent(
            generation_id=generation.id,
            node="content_generator",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=2,
            section_id="s-01",
        )
    )
    await recorder.apply_event(
        LLMCallSucceededEvent(
            generation_id=generation.id,
            node="content_generator",
            slot="standard",
            family="anthropic",
            model_name="claude-sonnet-4-6",
            attempt=2,
            section_id="s-01",
            latency_ms=2800.0,
            tokens_in=900,
            tokens_out=600,
            cost_usd=0.01,
        )
    )
    await recorder.apply_event(
        SectionReportUpdatedEvent(
            generation_id=generation.id,
            section_id="s-01",
            source="assembler",
            report=PipelineSectionReport(
                section_id="s-01",
                passed=True,
                warnings=["hook.body exceeds 80 words"],
            ),
        )
    )
    await recorder.apply_event(
        SectionRetryQueuedEvent(
            generation_id=generation.id,
            section_id="s-01",
            reason="Needs a cleaner practice progression",
            block_type="practice",
            next_attempt=2,
            max_attempts=3,
        )
    )
    await recorder.finalize_failure(error="Generation aborted after QC")

    report = await repo.load_report(generation.id)
    assert report.summary.total_llm_calls == 2
    assert report.summary.retry_count == 1
    assert report.summary.llm_transport_retries == 1
    assert report.summary.warning_count == 1
    assert report.sections[0].queued_retries[0].next_attempt == 2
    assert report.sections[0].nodes[0].llm_calls[0].status == "failed"
    assert report.sections[0].nodes[0].llm_calls[1].status == "succeeded"


@pytest.mark.asyncio
async def test_recorder_tracks_failed_sections_repairs_and_diagram_outcomes() -> None:
    generation = _generation("gen-failure-metrics")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Recoverable section",
            position=1,
        )
    )
    await recorder.apply_event(
        ValidationRepairAttemptedEvent(
            generation_id=generation.id,
            section_id="s-01",
            error_summary="Schema validation failed",
        )
    )
    await recorder.apply_event(
        ValidationRepairSucceededEvent(
            generation_id=generation.id,
            section_id="s-01",
        )
    )
    await recorder.apply_event(
        DiagramOutcomeEvent(
            generation_id=generation.id,
            section_id="s-01",
            outcome="skipped",
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            title="Lost section",
            position=2,
        )
    )
    await recorder.apply_event(
        SectionFailedEvent(
            generation_id=generation.id,
            section_id="s-02",
            title="Lost section",
            position=2,
            failed_at_node="content_generator",
            error_type="validation",
            error_summary="Schema validation failed after repair.",
            attempt_count=1,
            can_retry=True,
            missing_components=["section-header", "hook-hero"],
        )
    )
    await recorder.finalize_failure(error="Generation failed")

    report = await repo.load_report(generation.id)
    assert report.summary.validation_repair_attempts == 1
    assert report.summary.validation_repair_successes == 1
    assert not hasattr(report.summary, "diagram_skip_count")
    assert report.summary.failed_sections == 1
    assert any(section.section_id == "s-02" and section.status == "failed" for section in report.sections)


@pytest.mark.asyncio
async def test_recorder_tracks_image_interaction_and_field_regen_metrics() -> None:
    generation = _generation("gen-asset-telemetry")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Interactive section",
            position=1,
        )
    )
    await recorder.apply_event(
        ImageOutcomeEvent(
            generation_id=generation.id,
            section_id="s-01",
            outcome="success",
            provider="gemini",
        )
    )
    await recorder.apply_event(
        InteractionOutcomeEvent(
            generation_id=generation.id,
            section_id="s-01",
            outcome="generated",
            interaction_count=2,
        )
    )
    await recorder.apply_event(
        InteractionRetryQueuedEvent(
            generation_id=generation.id,
            section_id="s-01",
            next_attempt=2,
            reason="Simulation needs clearer controls",
        )
    )
    await recorder.apply_event(
        FieldRegenOutcomeEvent(
            generation_id=generation.id,
            section_id="s-01",
            field_name="hook",
            outcome="success",
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            title="Fallback section",
            position=2,
        )
    )
    await recorder.apply_event(
        ImageOutcomeEvent(
            generation_id=generation.id,
            section_id="s-02",
            outcome="timeout",
            error_message="Image generation timed out",
        )
    )
    await recorder.apply_event(
        InteractionOutcomeEvent(
            generation_id=generation.id,
            section_id="s-02",
            outcome="skipped",
            skip_reason="no_slot",
        )
    )
    await recorder.apply_event(
        FieldRegenOutcomeEvent(
            generation_id=generation.id,
            section_id="s-02",
            field_name="explanation",
            outcome="failed",
            error_message="Model returned invalid JSON",
        )
    )
    await recorder.finalize_failure(error="Generation failed")

    report = await repo.load_report(generation.id)
    section_one = next(section for section in report.sections if section.section_id == "s-01")
    section_two = next(section for section in report.sections if section.section_id == "s-02")

    assert section_one.image_outcome == "success"
    assert section_one.image_provider == "gemini"
    assert section_one.interaction_outcome == "generated"
    assert section_one.interaction_count == 2
    assert section_one.interaction_retry_count == 1
    assert section_one.field_regen_attempts[0].field == "hook"
    assert section_one.field_regen_attempts[0].outcome == "success"

    assert section_two.image_outcome == "timeout"
    assert section_two.image_error == "Image generation timed out"
    assert section_two.interaction_outcome == "skipped"
    assert section_two.interaction_skip_reason == "no_slot"
    assert section_two.field_regen_attempts[0].field == "explanation"
    assert section_two.field_regen_attempts[0].outcome == "failed"
    assert section_two.field_regen_attempts[0].error == "Model returned invalid JSON"

    assert report.summary.image_success_count == 1
    assert report.summary.image_failure_count == 1
    assert not hasattr(report.summary, "image_skip_count")
    assert report.summary.image_provider_counts == {"gemini": 1}
    assert report.summary.simulation_success_count == 1
    assert report.summary.interaction_skip_count == 1
    assert report.summary.interaction_retry_count == 1
    assert report.summary.field_regen_count == 2
    assert report.summary.field_regen_success_count == 1


@pytest.mark.asyncio
async def test_recorder_tracks_media_slot_metrics_and_required_media_blocks() -> None:
    generation = _generation("gen-media-slots")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        MediaPlanReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_count=2,
            slots=[
                {
                    "slot_id": "diagram-main",
                    "slot_type": "diagram",
                    "preferred_render_initial": "svg",
                    "preferred_render_final": "svg",
                    "fallback_render": None,
                    "decision_source": "slot_type_default",
                    "decision_reason": "slot_type=diagram, block_target=explanation",
                    "intelligent_prompt_resolved": False,
                },
                {
                    "slot_id": "simulation-lab",
                    "slot_type": "simulation",
                    "preferred_render_initial": "html_simulation",
                    "preferred_render_final": "html_simulation",
                    "fallback_render": "svg",
                    "decision_source": "slot_type_default",
                    "decision_reason": "slot_type=simulation, block_target=section",
                    "intelligent_prompt_resolved": False,
                },
            ],
        )
    )
    await recorder.apply_event(
        MediaSlotReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="diagram-main",
            slot_type="diagram",
            ready_frames=1,
            total_frames=1,
            svg_generation_mode="raw_svg",
            model_slot="standard",
            diagram_kind="coordinate_slope",
            sanitized=True,
            intent_validated=True,
        )
    )
    await recorder.apply_event(
        MediaSlotFailedEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="simulation-lab",
            slot_type="simulation",
            ready_frames=0,
            total_frames=1,
            error="Simulation HTML failed QC",
        )
    )
    await recorder.apply_event(
        SectionMediaBlockedEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_ids=["simulation-lab"],
            reason="Required media is still incomplete after retry exhaustion.",
        )
    )
    await recorder.apply_event(
        SectionRetryQueuedEvent(
            generation_id=generation.id,
            section_id="s-01",
            reason="Retrying required media frame.",
            block_type="simulation",
            next_attempt=2,
            max_attempts=2,
        )
    )
    await recorder.finalize_failure(error="Generation failed")

    report = await repo.load_report(generation.id)
    section = report.sections[0]

    assert section.media_slots_planned == 2
    assert section.media_slots_ready == 1
    assert section.media_slots_failed == 1
    assert section.media_frame_retry_count == 1
    assert section.media_blocked is True
    assert section.media_block_reason is not None
    assert [decision.status for decision in section.media_decisions] == ["generated", "failed"]
    assert section.simulation_outcome == "failed"
    assert report.summary.media_slots_planned == 2
    assert report.summary.media_slots_ready == 1
    assert report.summary.media_slots_failed == 1
    assert report.summary.media_frame_retry_count == 1
    assert report.summary.planned_svg_slots == 1
    assert report.summary.planned_simulation_slots == 1
    assert report.summary.raw_svg_generation_count == 1
    assert report.summary.svg_generation_model_slot == "standard"
    assert report.summary.svg_diagram_kind_counts == {"coordinate_slope": 1}
    assert report.summary.simulation_failure_count == 1


@pytest.mark.asyncio
async def test_recorder_tracks_raw_svg_failure_metadata() -> None:
    generation = _generation("gen-raw-svg-report")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        MediaPlanReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_count=3,
            slots=[
                {
                    "slot_id": "diagram-good",
                    "slot_type": "diagram",
                    "preferred_render_initial": "svg",
                    "preferred_render_final": "svg",
                    "decision_source": "slot_type_default",
                },
                {
                    "slot_id": "diagram-intent",
                    "slot_type": "diagram",
                    "preferred_render_initial": "svg",
                    "preferred_render_final": "svg",
                    "decision_source": "slot_type_default",
                },
                {
                    "slot_id": "diagram-validation",
                    "slot_type": "diagram",
                    "preferred_render_initial": "svg",
                    "preferred_render_final": "svg",
                    "decision_source": "slot_type_default",
                },
            ],
        )
    )
    await recorder.apply_event(
        MediaSlotReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="diagram-good",
            slot_type="diagram",
            ready_frames=1,
            total_frames=1,
            svg_generation_mode="raw_svg",
            model_slot="standard",
            diagram_kind="coordinate_slope",
            sanitized=True,
            intent_validated=True,
        )
    )
    await recorder.apply_event(
        MediaSlotFailedEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="diagram-intent",
            slot_type="diagram",
            ready_frames=0,
            total_frames=1,
            error="SVG appears to be a flowchart.",
            svg_generation_mode="raw_svg",
            model_slot="standard",
            sanitized=True,
            intent_validated=False,
            svg_failure_reason="intent",
        )
    )
    await recorder.apply_event(
        MediaSlotFailedEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="diagram-validation",
            slot_type="diagram",
            ready_frames=0,
            total_frames=1,
            error="SVG has no visible elements.",
            svg_generation_mode="raw_svg",
            model_slot="standard",
            sanitized=True,
            intent_validated=False,
            svg_failure_reason="validation",
        )
    )

    report = await repo.load_report(generation.id)
    section = report.sections[0]
    assert [decision.status for decision in section.media_decisions] == [
        "generated",
        "failed",
        "failed",
    ]
    assert section.media_decisions[1].svg_failure_reason == "intent"
    assert report.summary.raw_svg_generation_count == 3
    assert report.summary.svg_success_slots == 1
    assert report.summary.svg_failed_slots == 2
    assert report.summary.svg_intent_retry_count == 1
    assert report.summary.svg_validation_failure_count == 1
    assert report.summary.svg_sanitizer_failure_count == 0


@pytest.mark.asyncio
async def test_recorder_persists_runtime_outline_and_planner_trace() -> None:
    generation = _generation("gen-planner-trace")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        CurriculumPlannedEvent(
            generation_id=generation.id,
            path="seeded_enrichment",
            result="enriched",
            duplicate_term_warnings=[
                "Duplicate term assignment in curriculum plan term='slope' first_section='s-01' duplicate_section='s-02'"
            ],
            runtime_curriculum_outline=[
                {
                    "section_id": "s-01",
                    "title": "Intro to Slope",
                    "position": 1,
                    "role": "intro",
                    "focus": "Introduce slope as the steepness of a line.",
                    "terms_to_define": ["slope"],
                    "terms_assumed": [],
                    "practice_target": "identify slope as steepness from a graph",
                    "visual_placements_count": 1,
                }
            ],
            planner_trace_sections=[
                {
                    "section_id": "s-01",
                    "title": "Intro to Slope",
                    "position": 1,
                    "role": "intro",
                    "rationale_summary": "Introduce slope as the steepness of a line.",
                    "visual_placements_count": 1,
                    "visual_placements_summary": ["explanation:diagram"],
                }
            ],
        )
    )

    report = await repo.load_report(generation.id)
    assert report.runtime_curriculum_outline[0].terms_to_define == ["slope"]
    assert report.runtime_curriculum_outline[0].practice_target == (
        "identify slope as steepness from a graph"
    )
    assert report.planner_trace is not None
    assert report.planner_trace.path == "seeded_enrichment"
    assert report.planner_trace.result == "enriched"
    assert report.planner_trace.sections[0].rationale_summary == (
        "Introduce slope as the steepness of a line."
    )
    assert report.planner_trace.sections[0].visual_placements_count == 1
    assert report.planner_trace.sections[0].visual_placements_summary == [
        "explanation:diagram"
    ]
    assert report.summary.sections_with_planned_visuals == 1
    assert report.planner_trace.duplicate_term_warnings[0].startswith(
        "Duplicate term assignment in curriculum plan"
    )


@pytest.mark.asyncio
async def test_recorder_uses_plan_components_not_template_contract() -> None:
    generation = _generation("gen-plan-components")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        CurriculumPlannedEvent(
            generation_id=generation.id,
            path="seeded_passthrough",
            result="enriched",
            runtime_curriculum_outline=[
                {
                    "section_id": "s-01",
                    "title": "Practice section",
                    "position": 1,
                    "role": "practice",
                    "focus": "Apply the concept.",
                    "terms_to_define": [],
                    "terms_assumed": [],
                    "required_components": ["practice-stack", "student-textbox"],
                }
            ],
            planner_trace_sections=[],
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Practice section",
            position=1,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            attempt=1,
            trigger="initial",
        )
    )

    section = SectionContent(
        section_id="s-01",
        template_id="guided-concept-path",
        header=SectionHeaderContent(
            title="Practice section",
            subject="Calculus",
            grade_band="secondary",
        ),
        practice=PracticeContent(
            problems=[
                PracticeProblem(
                    difficulty="warm",
                    question="Practice question?",
                    hints=[PracticeHint(level=1, text="Hint")],
                )
            ]
        ),
        student_textbox=StudentTextboxContent(
            prompt="Write your answer.",
            lines=4,
        ),
    )
    await recorder.apply_event(
        SectionReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            section=section,
            completed_sections=1,
            total_sections=1,
        )
    )
    await recorder.finalize_success(
        document=_document(generation.id, [section]),
        generation_time_seconds=5.0,
    )

    report = await repo.load_report(generation.id)
    section_report = report.sections[0]
    assert set(section_report.expected_components) == {"practice", "student_textbox"}
    assert section_report.missing_components == []
    assert "explanation" not in section_report.expected_components
    assert "comparison_grid" not in section_report.expected_components
    assert "worked_example" not in section_report.expected_components


@pytest.mark.asyncio
async def test_recorder_timeline_excludes_noise_events() -> None:
    generation = _generation("gen-timeline-filter")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        PipelineStartEvent(
            generation_id=generation.id,
            section_count=1,
            template_id="guided-concept-path",
            preset_id="blue-classroom",
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Section",
            position=1,
        )
    )

    await recorder.apply_event(
        {
            "type": "node_started",
            "node": "schema_validator",
            "section_id": "s-01",
            "generation_id": generation.id,
            "attempt": 1,
        }
    )
    await recorder.apply_event(
        {
            "type": "node_finished",
            "node": "schema_validator",
            "section_id": "s-01",
            "generation_id": generation.id,
            "status": "succeeded",
            "attempt": 1,
            "latency_ms": 0.5,
        }
    )
    await recorder.apply_event(
        {
            "type": "section_partial",
            "section_id": "s-01",
            "generation_id": generation.id,
            "status": "partial",
            "pending_assets": [],
        }
    )
    await recorder.apply_event(
        {
            "type": "media_plan_ready",
            "section_id": "s-01",
            "generation_id": generation.id,
            "slot_count": 0,
        }
    )
    await recorder.apply_event(
        {
            "type": "image_outcome",
            "section_id": "s-01",
            "generation_id": generation.id,
            "outcome": "skipped",
        }
    )
    await recorder.apply_event(
        {
            "type": "diagram_outcome",
            "section_id": "s-01",
            "generation_id": generation.id,
            "outcome": "skipped",
        }
    )

    await recorder.finalize_failure(error="Test")
    report = await repo.load_report(generation.id)
    timeline_types = {item.type for item in report.timeline}

    assert "pipeline_start" in timeline_types
    assert "section_started" in timeline_types
    assert "node_started" not in timeline_types
    assert "node_finished" not in timeline_types
    assert "section_partial" not in timeline_types

    skipped_outcomes = [
        item
        for item in report.timeline
        if item.type in ("image_outcome", "diagram_outcome")
        and item.payload.get("outcome") == "skipped"
    ]
    assert skipped_outcomes == []

    zero_slot_plans = [
        item
        for item in report.timeline
        if item.type == "media_plan_ready" and item.payload.get("slot_count", 0) == 0
    ]
    assert zero_slot_plans == []


@pytest.mark.asyncio
async def test_recorder_tracks_visual_placement_and_render_mode_observability() -> None:
    generation = _generation("gen-visual-observability")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        VisualPlacementsCommittedEvent(
            generation_id=generation.id,
            section_id="s-01",
            placements_count=2,
            placements_summary=[
                "explanation:diagram:full_bleed",
                "worked_example:diagram:compact",
            ],
        )
    )
    await recorder.apply_event(
        MediaPlanReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_count=1,
            slots=[
                {
                    "slot_id": "diagram-main",
                    "slot_type": "diagram",
                    "preferred_render_initial": "svg",
                    "preferred_render_final": "image",
                    "fallback_render": "svg",
                    "decision_source": "intelligent_image_prompt",
                    "decision_reason": None,
                    "intelligent_prompt_resolved": True,
                }
            ],
        )
    )
    await recorder.apply_event(
        SlotRenderModeResolvedEvent(
            generation_id=generation.id,
            section_id="s-01",
            slot_id="diagram-main",
            render_mode="image",
            decided_by="intelligent_image_prompt",
            preferred_render_initial="svg",
            preferred_render_final="image",
            fallback_render="svg",
            intelligent_prompt_resolved=True,
        )
    )

    report = await repo.load_report(generation.id)
    section = report.sections[0]
    assert section.visual_placements_count == 2
    assert section.visual_placements_summary == [
        "explanation:diagram:full_bleed",
        "worked_example:diagram:compact",
    ]
    assert section.slot_render_modes == {"diagram-main": "image"}
    assert len(section.media_decisions) == 1
    assert section.media_decisions[0].decision_source == "intelligent_image_prompt"
    assert section.media_decisions[0].preferred_render_initial == "svg"
    assert section.media_decisions[0].preferred_render_final == "image"
    assert section.media_decisions[0].executor_selected == "image_generator"
    assert report.summary.image_slots_count == 1
    assert report.summary.svg_slots_count == 0
    assert report.summary.planned_image_slots == 1
    assert report.summary.prompt_builder_calls == 1


@pytest.mark.asyncio
async def test_recorder_tracks_selected_simulation_metadata() -> None:
    generation = _generation("gen-simulation-selection")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SimulationTypeSelectedEvent(
            generation_id=generation.id,
            section_id="s-01",
            simulation_type="timeline_scrubber",
            simulation_goal="Explore how the graph changes.",
        )
    )

    report = await repo.load_report(generation.id)
    section = report.sections[0]
    assert section.simulation_type_selected == "timeline_scrubber"
    assert section.simulation_goal_selected == "Explore how the graph changes."


@pytest.mark.asyncio
async def test_recorder_marks_terminal_failure_after_partial_progress() -> None:
    generation = _generation("gen-failed")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)

    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            title="Ready section",
            position=1,
        )
    )
    await recorder.apply_event(
        SectionStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            title="Lost section",
            position=2,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-01",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.apply_event(
        SectionReadyEvent(
            generation_id=generation.id,
            section_id="s-01",
            section=_section("s-01"),
            completed_sections=1,
            total_sections=2,
        )
    )
    await recorder.apply_event(
        SectionAttemptStartedEvent(
            generation_id=generation.id,
            section_id="s-02",
            attempt=1,
            trigger="initial",
        )
    )
    await recorder.finalize_failure(error="Provider outage")

    report = await repo.load_report(generation.id)
    assert report.status == "failed"
    assert report.outcome == "failed"
    assert report.summary.ready_sections == 1
    assert report.final_error == "Provider outage"
    assert any(section.section_id == "s-02" and section.status == "failed" for section in report.sections)


@pytest.mark.asyncio
async def test_recorder_consumer_keeps_running_after_bad_event() -> None:
    generation = _generation("gen-bad-event")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)
    processed: list[dict[str, str]] = []

    async def flaky_apply(event) -> None:
        processed.append(event)
        if len(processed) == 1:
            raise RuntimeError("boom")

    recorder.apply_event = flaky_apply  # type: ignore[method-assign]

    await recorder.start()
    event_bus.publish(generation.id, {"type": "bad"})
    event_bus.publish(generation.id, {"type": "good"})
    await asyncio.sleep(0.05)

    assert recorder.consumer_error is not None
    assert recorder.diagnostics_degraded is True
    assert recorder._consumer is not None
    assert recorder._consumer.done() is False

    await recorder.stop()


@pytest.mark.asyncio
async def test_wait_for_idle_drains_when_consumer_is_dead() -> None:
    generation = _generation("gen-dead-consumer")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)
    recorder._queue = asyncio.Queue()
    recorder._queue.put_nowait({"type": "stuck"})

    async def crash() -> None:
        raise RuntimeError("consumer died")

    recorder._consumer = asyncio.create_task(crash())
    await asyncio.sleep(0)

    await recorder.wait_for_idle(timeout=0.01)

    assert recorder.consumer_dead is True
    assert recorder.dropped_event_count == 1
    assert recorder.diagnostics_degraded is True
    assert recorder._consumer.exception() is not None


@pytest.mark.asyncio
async def test_wait_for_idle_times_out_and_drains_pending_queue() -> None:
    generation = _generation("gen-timeout-drain")
    repo = InMemoryReportRepo()
    recorder = GenerationReportRecorder(generation=generation, repository=repo)
    recorder._queue = asyncio.Queue()
    recorder._queue.put_nowait({"type": "pending"})

    await recorder.wait_for_idle(timeout=0.01)

    assert recorder.dropped_event_count == 1
    assert recorder.diagnostics_degraded is True
