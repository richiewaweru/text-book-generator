from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from v3_blueprint.planning.models import LessonSkeleton, SkeletonComponent, SkeletonSection
from v3_blueprint.skeleton.edit_planner import SkeletonEditPlan, run_skeleton_edit_planner
from v3_blueprint.skeleton.edits import SwapComponent


def _form() -> V3InputForm:
    return V3InputForm(
        grade_level="Grade 5",
        subject="Math",
        duration_minutes=30,
        topic="fractions",
        outcome="understand equivalence",
    )


def _signals() -> V3SignalSummary:
    return V3SignalSummary(
        topic="fractions",
        teacher_goal="equivalence",
        inferred_lesson_mode="first_exposure",
        lesson_mode_confidence="high",
    )


def _baseline() -> LessonSkeleton:
    return LessonSkeleton(
        lesson_mode="first_exposure",
        sections=[
            SkeletonSection(
                id="build",
                title="Build",
                role="build",
                visual_required=False,
                components=[SkeletonComponent(slug="explanation-block")],
            )
        ],
    )


@pytest.mark.asyncio
async def test_edit_planner_caps_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V3_SKELETON_DEVIATION_BUDGET", "1")
    bloated = SkeletonEditPlan(
        edits=[
            SwapComponent(
                section_id="build",
                from_slug="explanation-block",
                to_slug="key-fact",
                reason="one",
            ),
            SwapComponent(
                section_id="build",
                from_slug="key-fact",
                to_slug="definition-card",
                reason="two",
            ),
        ],
        unexpressible=[],
    )

    class _Result:
        output = bloated

    with (
        patch("v3_blueprint.skeleton.edit_planner.get_v3_model", return_value="model"),
        patch("v3_blueprint.skeleton.edit_planner.get_v3_spec", return_value=object()),
        patch("v3_blueprint.skeleton.edit_planner.get_v3_slot", return_value=object()),
        patch(
            "v3_blueprint.skeleton.edit_planner.structured_output_type_for_model",
            return_value=SkeletonEditPlan,
        ),
        patch("v3_blueprint.skeleton.edit_planner.Agent"),
        patch(
            "v3_blueprint.skeleton.edit_planner.run_llm",
            new=AsyncMock(return_value=_Result()),
        ),
        patch(
            "v3_blueprint.skeleton.edit_planner.get_v3_model_settings",
            return_value={},
        ),
    ):
        plan = await run_skeleton_edit_planner(
            signals=_signals(),
            form=_form(),
            resource_spec={"resource_type": "lesson", "depth": "standard"},
            baseline=_baseline(),
        )
    assert len(plan.edits) == 1
    assert any("over budget" in note for note in plan.unexpressible)


@pytest.mark.asyncio
async def test_edit_planner_malformed_survives() -> None:
    with (
        patch("v3_blueprint.skeleton.edit_planner.get_v3_model", return_value="model"),
        patch("v3_blueprint.skeleton.edit_planner.get_v3_spec", return_value=object()),
        patch("v3_blueprint.skeleton.edit_planner.get_v3_slot", return_value=object()),
        patch(
            "v3_blueprint.skeleton.edit_planner.structured_output_type_for_model",
            return_value=SkeletonEditPlan,
        ),
        patch("v3_blueprint.skeleton.edit_planner.Agent"),
        patch(
            "v3_blueprint.skeleton.edit_planner.run_llm",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
        patch(
            "v3_blueprint.skeleton.edit_planner.get_v3_model_settings",
            return_value={},
        ),
    ):
        plan = await run_skeleton_edit_planner(
            signals=_signals(),
            form=_form(),
            resource_spec={},
            baseline=_baseline(),
        )
    assert plan.edits == []
    assert plan.unexpressible
