"""Tests for stage-2 lanes that own brief → prose → questions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from v3_blueprint.planning.models import (
    AnchorSpec,
    ComponentBrief,
    ComponentSlot,
    LessonIntent,
    SectionBrief,
    SectionPlan,
    StructuralPlan,
)
from v3_blueprint.planning.retry import _failed_placeholder
from v3_execution.runtime.lanes import LaneOutcome
from v3_execution.runtime.stage2_lanes import run_stage2_lanes


def _minimal_plan() -> StructuralPlan:
    return StructuralPlan(
        lesson_mode="first_exposure",
        lesson_intent=LessonIntent(
            goal="Learn photosynthesis.",
            structure_rationale="Concrete first.",
        ),
        anchor=AnchorSpec(example="leaf", reuse_scope="all sections"),
        prior_knowledge=[],
        sections=[
            SectionPlan(
                id="orient",
                title="Orient",
                role="orient",
                visual_required=False,
                components=[ComponentSlot(slug="callout-card", purpose="hook")],
            ),
            SectionPlan(
                id="explain",
                title="Explain",
                role="explain",
                visual_required=False,
                components=[ComponentSlot(slug="explanation", purpose="core")],
            ),
        ],
        question_plan=[],
        answer_key_style="brief_explanations",
    )


def _form() -> V3InputForm:
    return V3InputForm(
        grade_level="Grade 8",
        subject="Science",
        duration_minutes=45,
        resource_type="lesson",
        topic="Photosynthesis",
        subtopics=[],
        prior_knowledge="",
        outcome="Explain photosynthesis.",
        struggle="",
        learner_level="on_grade",
        reading_level="on_grade",
        language_support="none",
        prior_knowledge_level="some_background",
        free_text="",
    )


def _signals() -> V3SignalSummary:
    return V3SignalSummary(
        topic="Photosynthesis",
        subtopic="Energy capture",
        prior_knowledge=[],
        learner_needs=[],
        teacher_goal="Build understanding",
        inferred_lesson_mode="first_exposure",
        lesson_mode_confidence="high",
    )


@pytest.mark.asyncio
async def test_run_stage2_lanes_returns_briefs_in_plan_order() -> None:
    plan = _minimal_plan()
    briefs_by_id = {
        "orient": SectionBrief(
            section_id="orient",
            components=[
                ComponentBrief(component_id="callout-card", content_intent="hook")
            ],
        ),
        "explain": SectionBrief(
            section_id="explain",
            components=[
                ComponentBrief(component_id="explanation", content_intent="core")
            ],
        ),
    }

    async def fake_run_all_lanes(*, lane_factories, **_kwargs):  # noqa: ANN001
        return [
            LaneOutcome(
                part_id="orient",
                brief=briefs_by_id["orient"],
                component_blocks=[{"id": "c"}],
            ),
            LaneOutcome(
                part_id="explain",
                brief=briefs_by_id["explain"],
                component_blocks=[{"id": "c2"}],
            ),
        ]

    with (
        patch(
            "v3_execution.runtime.stage2_lanes.load_chunked_state",
            new=AsyncMock(return_value={"section_briefs": {}}),
        ),
        patch(
            "v3_execution.runtime.stage2_lanes.run_all_lanes",
            new=AsyncMock(side_effect=fake_run_all_lanes),
        ),
    ):
        briefs = await run_stage2_lanes(
            "gen-1",
            plan=plan,
            signals=_signals(),
            form=_form(),
            resource_spec={"resource_type": "lesson"},
        )

    assert [b.section_id for b in briefs] == ["orient", "explain"]
    assert all(not getattr(b, "_failed", False) for b in briefs)


@pytest.mark.asyncio
async def test_run_stage2_lanes_marks_failed_brief_lane() -> None:
    plan = _minimal_plan()
    failed = _failed_placeholder("orient", ["boom"])

    async def fake_run_all_lanes(*, lane_factories, **_kwargs):  # noqa: ANN001
        return [
            LaneOutcome(part_id="orient", brief=failed, failed_step="brief"),
            LaneOutcome(
                part_id="explain",
                brief=SectionBrief(section_id="explain", components=[]),
            ),
        ]

    with (
        patch(
            "v3_execution.runtime.stage2_lanes.load_chunked_state",
            new=AsyncMock(return_value={"section_briefs": {}}),
        ),
        patch(
            "v3_execution.runtime.stage2_lanes.run_all_lanes",
            new=AsyncMock(side_effect=fake_run_all_lanes),
        ),
    ):
        briefs = await run_stage2_lanes(
            "gen-1",
            plan=plan,
            signals=_signals(),
            form=_form(),
            resource_spec={"resource_type": "lesson"},
        )

    assert getattr(briefs[0], "_failed", False) is True
    assert briefs[1].section_id == "explain"
