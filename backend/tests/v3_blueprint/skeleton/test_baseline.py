from __future__ import annotations

from resource_specs.loader import load_all_specs
from v3_blueprint.planning.validators import validate_lesson_skeleton
from v3_blueprint.skeleton.baseline import build_baseline_skeleton


def test_baseline_for_each_spec_and_depth() -> None:
    specs = load_all_specs()
    for spec in specs.values():
        for depth in spec.depth:
            skeleton = build_baseline_skeleton(spec, depth, active_supports=[])
            assert skeleton.sections
            assert len(skeleton.sections) <= spec.depth_limit(depth).max_sections
            errors = validate_lesson_skeleton(
                skeleton,
                {
                    "spec": {
                        "sections": {
                            "required": [{"role": s.role} for s in spec.sections.required],
                            "optional": [{"role": s.role} for s in spec.sections.optional],
                        }
                    }
                },
            )
            assert errors == [], (spec.id, depth, errors)


def test_baseline_includes_support_gated_optional() -> None:
    specs = load_all_specs()
    practice = specs["practice_set"]
    skeleton = build_baseline_skeleton(
        practice,
        "standard",
        active_supports=["worked_examples"],
    )
    roles = [s.role for s in skeleton.sections]
    assert "process" in roles
