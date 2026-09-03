"""Phase 01: deterministic Lectio-legal candidate intersection for lesson.yaml."""

from __future__ import annotations

from pathlib import Path

from contracts.lectio import MANUAL_ONLY_COMPONENT_IDS, get_component_card, get_planner_index
from resource_specs.candidates import (
    PAGE_PSEUDO_COMPONENT_IDS,
    iter_spec_component_ids,
    resolve_required_role_candidates,
    resolve_role_candidates,
    resolve_section_candidates,
)
from resource_specs.loader import (
    PRIMARY_RESOURCE_TYPE,
    get_primary_spec,
    initialize_registry,
    load_all_specs,
)
from resource_specs.schema import SectionSpec

SPECS_DIR = Path(__file__).parents[2] / "resources" / "specs"
EXPECTED_ARC = ("orient", "build", "model", "practice", "close")


def test_primary_resource_is_lesson() -> None:
    initialize_registry()
    assert PRIMARY_RESOURCE_TYPE == "lesson"
    primary = get_primary_spec()
    assert primary.id == "lesson"
    assert primary.version == "1.1"
    assert primary.required_roles() == list(EXPECTED_ARC)


def test_lesson_spec_every_component_exists_in_lectio_planner() -> None:
    specs = load_all_specs(SPECS_DIR)
    lesson = specs["lesson"]
    planner_ids = set(get_planner_index().get("component_ids") or [])
    for component_id in iter_spec_component_ids(lesson):
        assert component_id in planner_ids, f"{component_id} missing from planner_index"
        assert get_component_card(component_id) is not None
        assert component_id not in PAGE_PSEUDO_COMPONENT_IDS


def test_every_required_role_has_nonempty_legal_candidates() -> None:
    by_role = resolve_required_role_candidates()
    assert set(by_role) == set(EXPECTED_ARC)
    for role, candidates in by_role.items():
        assert candidates.candidates, f"role {role} has empty candidate set"
        assert candidates.role == role
        assert set(candidates.preferred).issubset(set(candidates.candidates))
        assert set(candidates.allowed).issubset(set(candidates.candidates))
        assert set(candidates.preferred).isdisjoint(set(candidates.allowed))


def test_candidate_intersection_is_deterministic() -> None:
    first = resolve_required_role_candidates()
    second = resolve_required_role_candidates()
    for role in EXPECTED_ARC:
        assert first[role].candidates == second[role].candidates
        assert first[role].preferred == second[role].preferred
        assert first[role].allowed == second[role].allowed
        assert first[role].excluded == second[role].excluded
        assert first[role].component_budget == second[role].component_budget


def test_forbidden_and_generation_excluded_do_not_leak() -> None:
    orient = resolve_role_candidates("orient")
    for forbidden in ("practice-stack", "quiz-check", "short-answer", "fill-in-blank"):
        assert forbidden not in orient.candidates

    # Visual writer_excluded components stay selectable for the visual lane.
    assert "diagram-block" in orient.candidates
    assert "image-block" not in orient.candidates
    assert "video-embed" not in orient.candidates

    lesson = get_primary_spec()
    section = SectionSpec(
        role="orient",
        intent="test",
        preferred_components=[
            "hook-hero",
            "practice-stack",
            *sorted(MANUAL_ONLY_COMPONENT_IDS),
        ],
        allowed_components=["callout-block", "diagram-block"],
        forbidden_components=["practice-stack"],
    )
    forced = resolve_section_candidates(section, spec=lesson)
    assert "practice-stack" not in forced.candidates
    assert forced.excluded["practice-stack"] == "role_forbidden"
    assert "diagram-block" in forced.candidates
    for manual_id in MANUAL_ONLY_COMPONENT_IDS:
        assert manual_id not in forced.candidates
        assert forced.excluded[manual_id] == "manual_only"
    assert "hook-hero" in forced.candidates
    assert "callout-block" in forced.candidates


def test_template_budget_filter_and_max_per_section_metadata() -> None:
    practice = resolve_role_candidates(
        "practice",
        remaining_budget={"practice-stack": 0},
    )
    assert "practice-stack" not in practice.candidates
    assert practice.excluded["practice-stack"] == "budget_exhausted"
    assert practice.candidates

    baseline = resolve_role_candidates("practice")
    assert "quiz-check" in baseline.candidates
    assert baseline.max_per_section.get("quiz-check") == 1
    assert baseline.max_per_section.get("practice-stack") == 1


def test_page_pseudo_components_never_appear_as_candidates() -> None:
    lesson = get_primary_spec()
    section = SectionSpec(
        role="build",
        intent="test",
        preferred_components=["definition-card", "prose", "table", "aside", "figure"],
        allowed_components=["page-block", "generic-card", "key-fact"],
        forbidden_components=[],
    )
    result = resolve_section_candidates(section, spec=lesson)
    for pseudo in PAGE_PSEUDO_COMPONENT_IDS:
        assert pseudo not in result.candidates
        if pseudo in result.excluded:
            assert result.excluded[pseudo] == "page_pseudo_component"
    assert "definition-card" in result.candidates
    assert "key-fact" in result.candidates


def test_close_forbids_worked_example_when_listed() -> None:
    close = resolve_role_candidates("close")
    assert "worked-example-card" not in close.candidates

    lesson = get_primary_spec()
    section = SectionSpec(
        role="close",
        intent="test",
        preferred_components=["summary-block", "worked-example-card"],
        allowed_components=[],
        forbidden_components=["worked-example-card"],
    )
    forced = resolve_section_candidates(section, spec=lesson)
    assert "worked-example-card" not in forced.candidates
    assert forced.excluded["worked-example-card"] == "role_forbidden"
    assert "summary-block" in forced.candidates

