from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.contracts import get_section_field_for_component

from v3_blueprint.models import ProductionBlueprint
from v3_execution.compile_orders import compile_execution_bundle
from v3_execution.component_aliases import canonical_component_id
from v3_execution.models import DraftPack, ExecutionResult, GeneratedAnswerKeyBlock
from v3_execution.runtime import events as v3_events
from v3_review import coherence_report_to_generation_summary
from v3_review.deterministic_checks import (
    check_expected_answers_preserved,
    check_internal_artifact_leaks,
    check_no_extra_questions,
    check_planned_sections_exist,
)
from v3_review.models import CoherenceReport
from v3_review.repair_router import route_repairs


def _load_example(filename: str) -> ProductionBlueprint:
    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / filename
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


def _concept_field() -> str:
    return get_section_field_for_component("explanation-block") or "explanation"


def _minimal_draft_pack(*, sections: list[dict], answer_key: GeneratedAnswerKeyBlock | None) -> DraftPack:
    return DraftPack(
        generation_id="g1",
        blueprint_id="b1",
        template_id="guided-concept-path",
        subject="Mathematics",
        status="draft_ready",
        sections=sections,
        answer_key=answer_key,
        warnings=[],
    )


def test_missing_planned_section_emits_blocking() -> None:
    bp = _load_example("amara_compound_area.json")
    partial_sections = [
        {
            "section_id": bp.sections[0].section_id,
            "template_id": "guided-concept-path",
            _concept_field(): {"body": "ok", "emphasis": []},
            "diagram": {"image_url": "https://example.com/a.png", "caption": "c", "alt_text": "c"},
        }
    ]
    dp = _minimal_draft_pack(
        sections=partial_sections,
        answer_key=GeneratedAnswerKeyBlock(
            answer_key_id="ak",
            style="answers_only",
            entries=[
                {"question_id": q.question_id, "student_answer": q.expected_answer}
                for q in bp.question_plan[:1]
            ],
            source_work_order_id="ak",
        ),
    )
    issues = check_planned_sections_exist(bp, dp)
    assert issues
    assert any(i.severity == "blocking" for i in issues)


def test_internal_leak_pattern_blocks() -> None:
    bp = _load_example("amara_compound_area.json")
    leak_body = "Look at wo_visual_01 for help."
    sections = []
    for sec_plan in bp.sections[:1]:
        sections.append(
            {
                "section_id": sec_plan.section_id,
                "template_id": "guided-concept-path",
                _concept_field(): {"body": leak_body, "emphasis": []},
                "diagram": {"image_url": "https://example.com/a.png", "caption": "c", "alt_text": "c"},
            }
        )
    dp = _minimal_draft_pack(
        sections=sections,
        answer_key=GeneratedAnswerKeyBlock(
            answer_key_id="ak",
            style="answers_only",
            entries=[
                {"question_id": q.question_id, "student_answer": q.expected_answer}
                for q in bp.question_plan[:1]
            ],
            source_work_order_id="ak",
        ),
    )
    issues = check_internal_artifact_leaks(dp)
    assert issues and issues[0].category == "internal_artifact_leak"


def test_extra_questions_major() -> None:
    bp = _load_example("amara_compound_area.json")
    practice_section_id = next(q.section_id for q in bp.question_plan)
    problems = [
        {"difficulty": "warm", "question": "a", "hints": [], "problem_type": "open"},
        {"difficulty": "warm", "question": "b", "hints": [], "problem_type": "open"},
        {"difficulty": "warm", "question": "c", "hints": [], "problem_type": "open"},
    ]
    sections = []

    def payload_for(field: str, intent: str) -> dict:
        if field == "explanation":
            return {"body": intent, "emphasis": []}
        if field == "worked_example":
            return {
                "title": intent,
                "solution": [{"step": "", "latex": "", "explain": "", "diagramRef": []}],
                "answer": "",
            }
        if field == "practice":
            return {"introduction": "", "items": [], "footnote": "", "diagram": None}
        if field == "summary":
            return {"paragraphs": [intent], "key_points": [], "cta": {}}
        return {"detail": intent}

    for sec_plan in bp.sections:
        bucket: dict = {
            "section_id": sec_plan.section_id,
            "template_id": "guided-concept-path",
        }
        for comp_planned in sec_plan.components:
            if (
                sec_plan.section_id == practice_section_id
                and comp_planned.component == "guided_questions"
            ):
                continue
            cid = canonical_component_id(comp_planned.component)
            field = get_section_field_for_component(cid) or "explanation"
            bucket[field] = payload_for(field, comp_planned.content_intent)

        if sec_plan.section_id == practice_section_id:
            bucket["practice"] = {
                "problems": problems,
                "label": "Practice Questions",
                "hints_visible_default": False,
                "solutions_available": True,
            }

        bucket["diagram"] = {"image_url": "https://example.com/a.png", "caption": "c", "alt_text": "c"}
        sections.append(bucket)

    dp = _minimal_draft_pack(
        sections=sections,
        answer_key=GeneratedAnswerKeyBlock(
            answer_key_id="ak",
            style="answers_only",
            entries=[
                {"question_id": q.question_id, "student_answer": q.expected_answer} for q in bp.question_plan
            ],
            source_work_order_id="ak",
        ),
    )
    issues = check_no_extra_questions(bp, dp)
    assert any(i.severity == "major" for i in issues)


def test_expected_answer_drift_in_answer_key() -> None:
    bp = _load_example("amara_compound_area.json")
    q0 = bp.question_plan[0]
    dp = _minimal_draft_pack(
        sections=[],
        answer_key=GeneratedAnswerKeyBlock(
            answer_key_id="ak",
            style="answers_only",
            entries=[{"question_id": q0.question_id, "student_answer": "wrong"}],
            source_work_order_id="ak",
        ),
    )
    issues = check_expected_answers_preserved(bp, dp)
    assert issues


def test_coherence_report_summary_json_safe() -> None:
    report = CoherenceReport(
        blueprint_id="b",
        generation_id="g",
        status="passed",
        deterministic_passed=True,
        llm_review_passed=True,
        issues=[],
        repair_targets=[],
    )
    summary = coherence_report_to_generation_summary(report)
    assert summary["status"] == "passed"
    assert summary["blocking_count"] == 0


@pytest.mark.asyncio
async def test_route_repairs_finalises_when_final_checks_patched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bp = _load_example("amara_compound_area.json")
    bundle = compile_execution_bundle(
        bp,
        generation_id="g1",
        blueprint_id="b1",
        template_id="guided-concept-path",
    )
    dp = _minimal_draft_pack(sections=[], answer_key=None)
    report = CoherenceReport(
        blueprint_id=dp.blueprint_id,
        generation_id=dp.generation_id,
        status="passed",
        deterministic_passed=True,
        llm_review_passed=True,
        issues=[],
        repair_targets=[],
    )
    exec_result = ExecutionResult(generation_id="g1", blueprint_id="b1")

    monkeypatch.setattr(
        "v3_review.repair_router.check_planned_sections_exist",
        lambda _bp, _dp: [],
    )
    monkeypatch.setattr(
        "v3_review.repair_router.check_planned_components_exist",
        lambda _bp, _dp: [],
    )
    monkeypatch.setattr(
        "v3_review.repair_router.check_planned_questions_exist",
        lambda _bp, _dp: [],
    )
    monkeypatch.setattr(
        "v3_review.repair_router.check_planned_visuals_exist",
        lambda _bp, _dp: [],
    )
    monkeypatch.setattr(
        "v3_review.repair_router.check_expected_answers_preserved",
        lambda _bp, _dp: [],
    )

    emitted: list[str] = []

    async def capture(ev: str, _: dict) -> None:
        emitted.append(ev)

    out_pack, out_report = await route_repairs(
        report,
        bp,
        bundle,
        dp,
        {},
        capture,
        exec_result,
        trace_id="t",
        generation_id="g1",
        model_overrides=None,
    )

    assert v3_events.RESOURCE_FINALISED in emitted
    assert out_pack.generation_id == dp.generation_id
    assert out_report.status == "passed"
