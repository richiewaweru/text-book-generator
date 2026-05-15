from __future__ import annotations

import json
from pathlib import Path

from contracts.lectio import get_section_field_for_component
from v3_blueprint.models import ProductionBlueprint
from v3_execution.assembly.section_builder import V3SectionBuilder
from v3_execution.component_aliases import canonical_component_id
from v3_execution.models import GeneratedComponentBlock, GeneratedQuestionBlock, GeneratedVisualBlock


def _load_example(filename: str) -> ProductionBlueprint:
    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / filename
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


def _component_payload(field: str, seed: str) -> dict:
    if field == "explanation":
        return {"body": seed, "emphasis": []}
    if field == "worked_example":
        return {
            "title": seed,
            "solution": [{"step": "", "latex": "", "explain": "", "diagramRef": []}],
            "answer": "",
        }
    if field == "summary":
        return {"paragraphs": [seed], "key_points": [], "cta": {}}
    if field == "hook":
        return {"headline": seed, "body": seed, "anchor": "anchor"}
    if field == "practice":
        return {"introduction": "", "items": [], "footnote": "", "diagram": None}
    return {"detail": seed}


def _build_component_blocks(blueprint: ProductionBlueprint) -> list[GeneratedComponentBlock]:
    out: list[GeneratedComponentBlock] = []
    for section in blueprint.sections:
        for idx, component in enumerate(section.components):
            component_id = canonical_component_id(component.component)
            field = get_section_field_for_component(component_id) or "explanation"
            out.append(
                GeneratedComponentBlock(
                    block_id=f"{section.section_id}-{component_id}",
                    section_id=section.section_id,
                    component_id=component_id,
                    section_field=field,
                    position=idx,
                    data=_component_payload(field, component.content_intent),
                    source_work_order_id=f"wo-{section.section_id}",
                )
            )
    return out


def _build_question_blocks(blueprint: ProductionBlueprint) -> list[GeneratedQuestionBlock]:
    out: list[GeneratedQuestionBlock] = []
    for q in blueprint.question_plan:
        out.append(
            GeneratedQuestionBlock(
                question_id=q.question_id,
                section_id=q.section_id,
                difficulty=q.temperature,
                data={
                    "question": q.prompt or q.question_id,
                    "difficulty": q.temperature,
                    "hints": [],
                    "problem_type": "open",
                },
                expected_answer=q.expected_answer,
                source_work_order_id=f"wo-q-{q.section_id}",
                diagram_required=q.diagram_required,
            )
        )
    return out


def _build_visual_blocks(blueprint: ProductionBlueprint) -> list[GeneratedVisualBlock]:
    out: list[GeneratedVisualBlock] = []
    for idx, sec in enumerate(blueprint.sections):
        out.append(
            GeneratedVisualBlock(
                visual_id=f"v-{idx}",
                attaches_to=sec.section_id,
                mode="diagram",
                image_url=f"https://cdn.example/{sec.section_id}.png",
                source_work_order_id=f"wo-v-{sec.section_id}",
                caption=sec.title,
                alt_text=sec.title,
            )
        )
    return out


def test_all_sections_complete_when_all_outputs_present() -> None:
    bp = _load_example("amara_compound_area.json")
    builder = V3SectionBuilder()
    sections, warnings, diagnostics = builder.build_sections(
        bp,
        _build_component_blocks(bp),
        _build_question_blocks(bp),
        _build_visual_blocks(bp),
        template_id="guided-concept-path",
        answer_key=None,
    )

    assert len(sections) == len(bp.sections)
    assert not warnings
    assert all(d.status == "complete" for d in diagnostics)


def test_missing_visual_marks_section_incomplete_but_keeps_renderable_sections() -> None:
    bp = _load_example("amara_compound_area.json")
    builder = V3SectionBuilder()
    visuals = _build_visual_blocks(bp)
    visuals = visuals[1:]
    sections, warnings, diagnostics = builder.build_sections(
        bp,
        _build_component_blocks(bp),
        _build_question_blocks(bp),
        visuals,
        template_id="guided-concept-path",
        answer_key=None,
    )

    assert sections
    assert warnings
    assert any(d.status == "incomplete" for d in diagnostics)


def test_missing_component_marks_section_incomplete() -> None:
    bp = _load_example("amara_compound_area.json")
    builder = V3SectionBuilder()
    components = _build_component_blocks(bp)
    components = components[1:]
    sections, warnings, diagnostics = builder.build_sections(
        bp,
        components,
        _build_question_blocks(bp),
        _build_visual_blocks(bp),
        template_id="guided-concept-path",
        answer_key=None,
    )

    assert sections
    assert warnings
    assert any(d.missing_components for d in diagnostics)


def test_one_section_can_fail_without_collapsing_whole_pack() -> None:
    bp = _load_example("amara_compound_area.json")
    builder = V3SectionBuilder()
    failed_section = bp.sections[0].section_id
    components = [c for c in _build_component_blocks(bp) if c.section_id != failed_section]
    visuals = [v for v in _build_visual_blocks(bp) if v.attaches_to != failed_section]
    questions = [q for q in _build_question_blocks(bp) if q.section_id != failed_section]
    sections, warnings, diagnostics = builder.build_sections(
        bp,
        components,
        questions,
        visuals,
        template_id="guided-concept-path",
        answer_key=None,
    )

    assert len(sections) < len(bp.sections)
    assert warnings
    failed_diag = next(d for d in diagnostics if d.section_id == failed_section)
    assert failed_diag.status in {"failed", "incomplete"}
    assert not failed_diag.renderable


def test_no_sections_assemble_when_no_component_outputs_exist() -> None:
    bp = _load_example("amara_compound_area.json")
    builder = V3SectionBuilder()
    sections, warnings, diagnostics = builder.build_sections(
        bp,
        [],
        [],
        [],
        template_id="guided-concept-path",
        answer_key=None,
    )

    assert sections == []
    assert warnings
    assert all(not d.renderable for d in diagnostics)
