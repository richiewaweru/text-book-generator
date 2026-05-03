from __future__ import annotations

from pathlib import Path

from resource_specs.loader import load_all_specs

SPECS_DIR = Path(__file__).parents[2] / "resources" / "specs"


def test_all_resource_specs_load() -> None:
    specs = load_all_specs(SPECS_DIR)
    assert set(specs) == {
        "mini_booklet",
        "worksheet",
        "exit_ticket",
        "quick_explainer",
        "practice_set",
        "quiz",
    }


def test_specs_have_required_sections_and_depths() -> None:
    specs = load_all_specs(SPECS_DIR)
    for spec in specs.values():
        assert spec.sections.required
        assert {"quick", "standard", "deep"}.issubset(spec.depth)
        for depth_key in ("quick", "standard", "deep"):
            depth_variant = spec.depth[depth_key]
            assert isinstance(depth_variant.min_sections, int)
            assert isinstance(depth_variant.max_sections, int)
            assert depth_variant.min_sections <= depth_variant.max_sections
