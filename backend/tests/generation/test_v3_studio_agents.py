from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from generation.v3_studio.agents import (
    extract_signals,
    form_to_lens_hints,
    generate_production_blueprint,
    get_clarifications,
)
from generation.v3_studio.dtos import V3InputForm, V3SignalSummary
from generation.v3_studio.dtos import ProductionBlueprintEnvelope
from v3_blueprint.models import ProductionBlueprint


def _example_form(**overrides: Any) -> V3InputForm:
    payload = {
        "grade_level": "Grade 7",
        "subject": "Mathematics",
        "duration_minutes": 50,
        "topic": "Compound area",
        "subtopics": ["L-shapes", "Decompose into rectangles"],
        "prior_knowledge": "Rectangle area",
        "lesson_mode": "first_exposure",
        "intended_outcome": "understand",
        "learner_level": "on_grade",
        "reading_level": "on_grade",
        "language_support": "some_ell",
        "prior_knowledge_level": "some_background",
        "support_needs": ["visuals", "worked_examples"],
        "learning_preferences": ["step_by_step"],
        "free_text": "Use real-world floorplan examples if possible.",
    }
    payload.update(overrides)
    return V3InputForm(**payload)


@pytest.mark.asyncio
async def test_extract_signals_includes_structured_form_in_user_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_run_llm(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return type(
            "Result",
            (),
            {
                "output": V3SignalSummary(
                    topic="Compound area",
                    subtopic=None,
                    prior_knowledge=[],
                    learner_needs=[],
                    teacher_goal="Learners can decompose shapes to find area.",
                    inferred_resource_type="lesson",
                    confidence="high",
                    missing_signals=[],
                )
            },
        )()

    monkeypatch.setattr("generation.v3_studio.agents.run_llm", fake_run_llm)

    form = _example_form()
    _ = await extract_signals(form, trace_id="tid-test")

    user_prompt = str(captured.get("user_prompt", ""))
    assert "Grade level: Grade 7" in user_prompt
    assert "Topic: Compound area" in user_prompt
    assert "Subtopics: L-shapes, Decompose into rectangles" in user_prompt
    assert "Lesson mode: first_exposure" in user_prompt
    assert "Learning preferences: step_by_step" in user_prompt


@pytest.mark.asyncio
async def test_generate_blueprint_passes_retry_policy_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_run_llm(**kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        raw = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "v3_blueprint"
            / "examples"
            / "amara_compound_area.json"
        )
        bp = ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))
        return type("Result", (), {"output": ProductionBlueprintEnvelope(blueprint=bp)})()

    monkeypatch.setattr("generation.v3_studio.agents.run_llm", fake_run_llm)

    form = _example_form()
    signals = V3SignalSummary(
        topic="Compound area",
        subtopic="L-shapes",
        prior_knowledge=[],
        learner_needs=[],
        teacher_goal="Learners can decompose shapes to find area.",
        inferred_resource_type="lesson",
        confidence="high",
        missing_signals=[],
    )

    _ = await generate_production_blueprint(
        signals=signals,
        form=form,
        clarification_answers=[],
        trace_id="tid-test",
    )

    retry_policy = captured.get("retry_policy")
    assert retry_policy is not None
    assert getattr(retry_policy, "call_timeout_seconds", None) is not None
    user_prompt = str(captured.get("user_prompt", ""))
    assert "FormLensHints:" in user_prompt
    assert "lesson_mode: first_exposure" in user_prompt


def test_form_to_lens_hints_contains_key_fields() -> None:
    hints = form_to_lens_hints(_example_form())
    assert "lesson_mode: first_exposure" in hints
    assert "learner_level: on_grade" in hints
    assert "reading_level: on_grade" in hints
    assert "language_support: some_ell" in hints
    assert "support_needs: visuals, worked_examples" in hints


@pytest.mark.asyncio
async def test_get_clarifications_skips_llm_when_form_is_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"run_llm": False}

    async def fake_run_llm(**_kwargs):  # type: ignore[no-untyped-def]
        called["run_llm"] = True
        return type("Result", (), {"output": type("Raw", (), {"questions": []})()})()

    monkeypatch.setattr("generation.v3_studio.agents.run_llm", fake_run_llm)

    form = _example_form()
    signals = V3SignalSummary(
        topic="Compound area",
        subtopic="L-shapes",
        prior_knowledge=[],
        learner_needs=[],
        teacher_goal="Learners can decompose shapes to find area.",
        inferred_resource_type="lesson",
        confidence="high",
        missing_signals=[],
    )

    qs = await get_clarifications(signals, form, trace_id="tid-test")
    assert qs == []
    assert called["run_llm"] is False


@pytest.mark.asyncio
async def test_get_clarifications_calls_llm_when_form_is_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"run_llm": False}

    async def fake_run_llm(**_kwargs):  # type: ignore[no-untyped-def]
        called["run_llm"] = True
        return type("Result", (), {"output": type("Raw", (), {"questions": []})()})()

    monkeypatch.setattr("generation.v3_studio.agents.run_llm", fake_run_llm)

    form = _example_form(topic="")
    signals = V3SignalSummary(
        topic="",
        subtopic=None,
        prior_knowledge=[],
        learner_needs=[],
        teacher_goal="Needs topic clarification.",
        inferred_resource_type="lesson",
        confidence="low",
        missing_signals=["topic"],
    )

    _ = await get_clarifications(signals, form, trace_id="tid-test")
    assert called["run_llm"] is True

