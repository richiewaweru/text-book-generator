from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.contracts import get_section_field_for_component

from v3_blueprint.models import ProductionBlueprint
from v3_execution.compile_orders import compile_execution_bundle
from v3_execution.models import (
    GeneratedAnswerKeyBlock,
    GeneratedComponentBlock,
    GeneratedQuestionBlock,
    GeneratedVisualBlock,
    QuestionWriterWorkOrder,
    VisualGeneratorWorkOrder,
    WriterQuestion,
)
from v3_execution.runtime import validation as v
from v3_execution.runtime import events as v3_events
from v3_execution.runtime.runner import run_generation
from v3_review.models import CoherenceReport


def _load_example(filename: str) -> ProductionBlueprint:
    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / filename
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


def test_compile_execution_bundle() -> None:
    bp = _load_example("amara_compound_area.json")
    bundle = compile_execution_bundle(
        bp,
        generation_id="g1",
        blueprint_id="b1",
        template_id="diagram-led",
    )
    assert bundle.section_orders
    assert bundle.question_orders
    assert bundle.visual_orders
    assert bundle.answer_key_order is not None


def test_validate_visual_accepts_http_scheme() -> None:
    from v3_execution.models import VisualPlanItem

    order = VisualGeneratorWorkOrder(
        work_order_id="v1",
        visual=VisualPlanItem(id="v1", attaches_to="practice"),
        source_of_truth=[],
    )
    bad_scheme = GeneratedVisualBlock(
        visual_id="v1",
        attaches_to="practice",
        mode="diagram",
        image_url="ftp://bad",
        source_work_order_id="v1",
    )
    errs = v.validate_visual_block(bad_scheme, order)
    assert errs

    good = GeneratedVisualBlock(
        visual_id="v1",
        attaches_to="practice",
        mode="diagram",
        image_url="https://cdn.example/image.png",
        source_work_order_id="v1",
    )
    assert not v.validate_visual_block(good, order)


def test_validate_question_block_rejects_answer_drift() -> None:
    order = QuestionWriterWorkOrder(
        work_order_id="q1",
        section_id="practice",
        questions=[
            WriterQuestion(id="q1", difficulty="warm", expected_answer="nine"),
        ],
        source_of_truth=[],
    )
    block = GeneratedQuestionBlock(
        question_id="q1",
        section_id="practice",
        difficulty="warm",
        data={"question": "?"},
        expected_answer="wrong",
        source_work_order_id="q1",
    )
    assert v.validate_question_block(block, order)


@pytest.mark.asyncio
async def test_runner_with_stubbed_executors(monkeypatch: pytest.MonkeyPatch) -> None:
    bp = _load_example("amara_compound_area.json")

    async def stub_section(order, emit, **_: object) -> list[GeneratedComponentBlock]:
        blocks: list[GeneratedComponentBlock] = []
        for position, component in enumerate(order.section.components):
            field = get_section_field_for_component(component.component_id) or "explanation"
            if field == "explanation":
                payload = {"body": component.content_intent, "emphasis": []}
            elif field == "worked_example":
                payload = {
                    "title": component.content_intent,
                    "solution": [{"step": "", "latex": "", "explain": "", "diagramRef": []}],
                    "answer": "",
                }
            elif field == "summary":
                payload = {"paragraphs": [component.content_intent], "key_points": [], "cta": {}}
            elif field == "hook":
                payload = {
                    "headline": component.content_intent,
                    "body": component.content_intent,
                    "anchor": "anchor",
                }
            elif field == "practice":
                payload = {"introduction": "", "items": [], "footnote": "", "diagram": None}
            else:
                payload = {"detail": component.content_intent}
            blk = GeneratedComponentBlock(
                block_id=f"b-{component.component_id}",
                section_id=order.section.id,
                component_id=component.component_id,
                section_field=field,
                position=position,
                data=payload,
                source_work_order_id=order.work_order_id,
            )
            blocks.append(blk)
            await emit(
                "component_ready",
                {
                    "component_id": blk.component_id,
                    "section_id": blk.section_id,
                    "data": blk.data,
                },
            )
        return blocks

    async def stub_questions(
        order,
        emit,
        **_: object,
    ) -> list[GeneratedQuestionBlock]:
        out: list[GeneratedQuestionBlock] = []
        for question in order.questions:
            out.append(
                GeneratedQuestionBlock(
                    question_id=question.id,
                    section_id=order.section_id,
                    difficulty=question.difficulty,
                    data={
                        "question": question.id,
                        "difficulty": question.difficulty,
                        "hints": [],
                        "problem_type": "open",
                    },
                    expected_answer=question.expected_answer,
                    source_work_order_id=order.work_order_id,
                )
            )
        await emit("question_ready", {"section_id": order.section_id})
        return out

    async def stub_visual(order, emit, **_kwargs) -> list[GeneratedVisualBlock]:
        blk = GeneratedVisualBlock(
            visual_id=order.visual.id,
            attaches_to=order.visual.attaches_to,
            mode="diagram",
            image_url="http://localhost/generated.png",
            source_work_order_id=order.work_order_id,
            caption="caption",
            alt_text="caption",
        )
        await emit("visual_ready", {"visual_id": blk.visual_id})
        return [blk]

    async def noop_answer(order, emit, **_kwargs) -> GeneratedAnswerKeyBlock:  # noqa: ARG002
        return GeneratedAnswerKeyBlock(
            answer_key_id="ak",
            style="answers_only",
            entries=[{"question_id": q.id, "student_answer": q.expected_answer} for q in order.questions],
            source_work_order_id=order.work_order_id,
        )

    monkeypatch.setattr("v3_execution.runtime.runner.execute_section", stub_section)
    monkeypatch.setattr("v3_execution.runtime.runner.execute_questions", stub_questions)
    monkeypatch.setattr("v3_execution.runtime.runner.execute_visual", stub_visual)
    monkeypatch.setattr("v3_execution.runtime.runner.execute_answer_key", noop_answer)

    async def stub_coherence_review(
        blueprint,
        draft_pack,
        manifest,
        emit_event,
        **_kwargs: object,
    ) -> CoherenceReport:
        _ = blueprint
        _ = manifest
        _ = emit_event
        return CoherenceReport(
            blueprint_id=draft_pack.blueprint_id,
            generation_id=draft_pack.generation_id,
            status="passed",
            deterministic_passed=True,
            llm_review_passed=True,
            issues=[],
            repair_targets=[],
        )

    async def stub_route_repairs(
        report,
        blueprint,
        work_orders,
        draft_pack,
        manifest,
        emit_event,
        execution_result,
        **_kwargs: object,
    ):
        _ = blueprint
        _ = work_orders
        _ = manifest
        _ = execution_result
        await emit_event(
            v3_events.RESOURCE_FINALISED,
            {"generation_id": draft_pack.generation_id, "status": report.status},
        )
        return draft_pack, report

    monkeypatch.setattr("v3_execution.runtime.runner.run_coherence_review", stub_coherence_review)
    monkeypatch.setattr("v3_execution.runtime.runner.route_repairs", stub_route_repairs)

    captured: list[str] = []

    async def capture(event_type: str, payload: dict) -> None:
        captured.append(event_type)

    result = await run_generation(
        blueprint=bp,
        generation_id="g-x",
        blueprint_id="b-x",
        template_id="diagram-led",
        emit_event=capture,
        model_overrides=None,
    )

    assert result.component_blocks
    assert result.question_blocks
    assert result.visual_blocks
    assert result.answer_key
    assert "draft_pack_ready" in captured
    assert "resource_finalised" in captured

