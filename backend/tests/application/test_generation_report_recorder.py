from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pipeline.api import PipelineDocument, PipelineSectionReport
from pipeline.events import (
    LLMCallFailedEvent,
    LLMCallStartedEvent,
    LLMCallSucceededEvent,
    NodeFinishedEvent,
    NodeStartedEvent,
    PipelineStartEvent,
    SectionAttemptStartedEvent,
    SectionReadyEvent,
    SectionReportUpdatedEvent,
    SectionRetryQueuedEvent,
    SectionStartedEvent,
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
from textbook_agent.application.dtos import GenerationReport
from textbook_agent.application.services.generation_report_recorder import (
    GenerationReportRecorder,
)
from textbook_agent.domain.entities.generation import Generation


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generation(generation_id: str = "gen-report") -> Generation:
    return Generation(
        id=generation_id,
        user_id="user-1",
        subject="Calculus",
        context="Explain limits",
        mode="balanced",
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
        mode="balanced",
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
            mode="balanced",
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
    assert report.summary.warning_count == 1
    assert report.sections[0].queued_retries[0].next_attempt == 2
    assert report.sections[0].nodes[0].llm_calls[0].status == "failed"
    assert report.sections[0].nodes[0].llm_calls[1].status == "succeeded"


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
