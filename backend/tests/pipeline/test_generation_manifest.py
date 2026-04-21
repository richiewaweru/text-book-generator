from __future__ import annotations

from pipeline.contracts import build_section_generation_manifest
from pipeline.types.requests import SectionPlan


def test_generation_manifest_resolves_fields_hints_capacity_and_schema() -> None:
    plan = SectionPlan(
        section_id="s-01",
        title="Summary section",
        position=1,
        focus="Consolidate ideas",
        required_components=["summary-block", "callout-block"],
        optional_components=[],
    )

    manifest = build_section_generation_manifest(
        template_id="guided-concept-path",
        section_plan=plan,
    )
    by_component = {field.component_id: field for field in manifest.required_fields}

    assert by_component["summary-block"].field_name == "summary"
    assert by_component["callout-block"].field_name == "callout"
    assert by_component["summary-block"].generation_hint
    assert by_component["summary-block"].capacity
    assert by_component["summary-block"].schema


def test_generation_manifest_classifies_external_media_fields() -> None:
    plan = SectionPlan(
        section_id="s-02",
        title="Visual section",
        position=2,
        focus="Use visuals",
        required_components=["diagram-block", "video-embed"],
        optional_components=["image-block"],
    )

    manifest = build_section_generation_manifest(
        template_id="guided-concept-path",
        section_plan=plan,
    )
    external_components = {field.component_id for field in manifest.external_fields}

    assert "diagram-block" in external_components
    assert "video-embed" in external_components
    assert "image-block" in external_components
