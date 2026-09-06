from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from generation.contracts import GenerationInputForm as V3InputForm
from generation.contracts import GenerationSignalSummary as V3SignalSummary
from v3_blueprint.planning import retry, structural_planner
from v3_blueprint.planning.models import (
    AnchorSpec,
    IntentPlan,
    IntentSectionPlan,
    LessonIntent,
    QPlanItem,
    StructuralPlan,
)


def _signals() -> V3SignalSummary:
    return V3SignalSummary(
        topic="Fractions",
        subtopic="Equivalent fractions",
        prior_knowledge=["equal sharing"],
        learner_needs=[],
        teacher_goal="Build confidence",
        inferred_lesson_mode="first_exposure",
        lesson_mode_confidence="high",
    )


def _form() -> V3InputForm:
    return V3InputForm(
        grade_level="Grade 6",
        subject="Math",
        duration_minutes=45,
        resource_type="lesson",
        topic="Equivalent fractions",
        subtopics=["pizza slices"],
        prior_knowledge="equal sharing",
        outcome="Students can identify and generate equivalent fractions.",
        struggle="Some learners still mix up numerator and denominator.",
        learner_level="on_grade",
        reading_level="on_grade",
        language_support="none",
        prior_knowledge_level="some_background",
        free_text="",
    )


def _intent_plan(*, role: str = "orient", section_id: str = "orient") -> IntentPlan:
    return IntentPlan(
        lesson_mode="first_exposure",
        lesson_intent=LessonIntent(
            goal="By the end students can compare fractions.",
            structure_rationale="Concrete-first structure for novice learners.",
        ),
        anchor=AnchorSpec(
            example="splitting a pizza into 8 equal slices",
            reuse_scope="used in orient and practice",
        ),
        prior_knowledge=["equal sharing"],
        sections=[
            IntentSectionPlan(
                id=section_id,
                title="Orient",
                role=role,
                purpose="Surface the pizza-sharing conflict before teaching.",
                must_establish=["anchor visible"],
                misconception_focus=[],
                card_id=None,
                visual_required=False,
                transition_note=None,
            )
        ],
        question_plan=[
            QPlanItem(
                question_id="q1",
                section_id=section_id,
                temperature="warm",
                diagram_required=False,
            )
        ],
        answer_key_style="brief_explanations",
    )


def _structural_from_intent(*, role: str = "orient", section_id: str = "orient") -> StructuralPlan:
    from v3_blueprint.planning.models import intent_plan_to_structural_plan

    return intent_plan_to_structural_plan(_intent_plan(role=role, section_id=section_id))


def test_stage1_uses_helper_backstop_without_node_level_cap() -> None:
    assert not hasattr(structural_planner, "STAGE1_MAX_TOKENS")


@pytest.mark.asyncio
async def test_call_stage1_prints_traceback_and_reraises() -> None:
    signals = _signals()
    form = _form()
    error = RuntimeError("llm blew up")

    with (
        patch.object(structural_planner, "build_stage1_system_prompt", return_value="prompt"),
        patch.object(structural_planner, "run_llm", new=AsyncMock(side_effect=error)),
        patch("builtins.print") as mock_print,
    ):
        with pytest.raises(RuntimeError, match="llm blew up"):
            await structural_planner._call_stage1(
                signals,
                form,
                {"resource_type": "lesson"},
                generation_id="gen-123",
            )

    mock_print.assert_called_once()
    printed = mock_print.call_args.args[0]
    assert "[_CALL_STAGE1 ERROR]" in printed
    assert "generation_id=gen-123" in printed
    assert "type=RuntimeError" in printed
    assert "message=llm blew up" in printed
    assert mock_print.call_args.kwargs["flush"] is True


@pytest.mark.asyncio
async def test_call_stage1_uses_shared_model_settings_helper() -> None:
    signals = _signals()
    form = _form()
    valid_intent = _intent_plan()

    with (
        patch.dict(
            "os.environ",
            {
                "V3_STANDARD_PROVIDER": "openai_compatible",
                "V3_STANDARD_MODEL_NAME": "deepseek-v4-pro",
                "V3_STANDARD_BASE_URL": "https://api.deepseek.com",
                "V3_STANDARD_API_KEY_ENV": "DEEPSEEK_API_KEY",
                "DEEPSEEK_API_KEY": "test-deepseek-key",
            },
        ),
        patch.object(structural_planner, "build_stage1_system_prompt", return_value="prompt"),
        patch.object(
            structural_planner,
            "run_llm",
            new=AsyncMock(return_value=type("Result", (), {"output": valid_intent})()),
        ) as mock_run_llm,
    ):
        await structural_planner._call_stage1(
            signals,
            form,
            {
                "resource_type": "lesson",
                "spec": {"sections": {"required": [{"role": "orient"}]}},
            },
            generation_id="gen-stage1-settings",
        )

    call_kwargs = mock_run_llm.await_args.kwargs
    assert call_kwargs["model_settings"] == {
        "openai_reasoning_effort": "high",
        "extra_body": {"thinking": {"type": "enabled"}},
        "max_tokens": 120000,
    }


@pytest.mark.asyncio
async def test_run_stage1_with_retry_retries_truncation_and_returns_second_attempt() -> None:
    signals = _signals()
    form = _form()
    valid_plan = _structural_from_intent()

    with patch.object(
        retry,
        "_call_stage1",
        new=AsyncMock(
            side_effect=[
                retry.TruncatedCompletionError(
                    node="v3_stage1_planner",
                    finish_reason="length",
                    detail="Model completion was truncated before a complete response was produced",
                ),
                valid_plan,
            ]
        ),
    ) as mock_call_stage1, patch.object(retry, "validate_structural_plan", return_value=[]):
        result = await retry.run_stage1_with_retry(
            signals,
            form,
            {
                "resource_type": "lesson",
                "spec": {"sections": {"required": [{"role": "orient"}]}},
            },
            generation_id=None,
            trace_id="trace-stage1-truncation",
        )

    assert result == valid_plan
    assert mock_call_stage1.await_count == 2


@pytest.mark.asyncio
async def test_run_stage1_with_retry_prints_attempt_exception_and_reraises() -> None:
    signals = _signals()
    form = _form()
    error = ValueError("bad stage1")

    with (
        patch.object(retry, "_call_stage1", new=AsyncMock(side_effect=error)),
        patch("builtins.print") as mock_print,
    ):
        with pytest.raises(ValueError, match="bad stage1"):
            await retry.run_stage1_with_retry(
                signals,
                form,
                {"resource_type": "lesson"},
                generation_id="gen-456",
                trace_id="trace-456",
            )

    mock_print.assert_called_once()
    printed = mock_print.call_args.args[0]
    assert "[STAGE1 ATTEMPT 1 EXCEPTION]" in printed
    assert "generation_id=gen-456" in printed
    assert "type=ValueError" in printed
    assert mock_print.call_args.kwargs["flush"] is True


@pytest.mark.asyncio
async def test_call_stage1_rejects_role_outside_active_resource_spec() -> None:
    signals = _signals()
    form = _form()
    invalid_intent = _intent_plan(role="invalid_role", section_id="intro")

    with patch.object(
        structural_planner,
        "run_llm",
        new=AsyncMock(return_value=type("Result", (), {"output": invalid_intent})()),
    ), patch.object(structural_planner, "build_stage1_system_prompt", return_value="prompt"):
        with pytest.raises(ValueError, match="which is not among active resource spec roles"):
            await structural_planner._call_stage1(
                signals,
                form,
                {
                    "resource_type": "lesson",
                    "spec": {
                        "sections": {
                            "required": [
                                {"role": "orient"},
                                {"role": "practice"},
                            ]
                        }
                    },
                },
                generation_id="gen-role-guard",
            )
