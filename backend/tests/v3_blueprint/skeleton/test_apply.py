from __future__ import annotations

from resource_specs.loader import get_spec
from v3_blueprint.planning.validators import validate_lesson_skeleton
from v3_blueprint.skeleton.apply import apply_edits
from v3_blueprint.skeleton.baseline import build_baseline_skeleton
from v3_blueprint.skeleton.edits import (
    AddComponent,
    RemoveComponent,
    SetVisual,
    SwapComponent,
)


def _resource_spec_dict(spec_id: str = "lesson") -> dict:
    spec = get_spec(spec_id)
    return {
        "spec": {
            "sections": {
                "required": [{"role": s.role} for s in spec.sections.required],
                "optional": [{"role": s.role} for s in spec.sections.optional],
            }
        }
    }


def test_legal_swap_applies() -> None:
    spec = get_spec("lesson")
    baseline = build_baseline_skeleton(spec, "standard", [])
    section = next(s for s in baseline.sections if s.role == "build")
    from_slug = section.components[0].slug
    allowed = sorted(spec.all_allowed_components_for_role("build") - {from_slug})
    assert allowed
    to_slug = allowed[0]
    edited, rejected = apply_edits(
        baseline,
        [
            SwapComponent(
                section_id=section.id,
                from_slug=from_slug,
                to_slug=to_slug,
                reason="test",
            )
        ],
        spec,
        depth="standard",
    )
    assert rejected == []
    new_section = next(s for s in edited.sections if s.id == section.id)
    assert to_slug in [c.slug for c in new_section.components]
    assert validate_lesson_skeleton(edited, _resource_spec_dict()) == []


def test_illegal_fifth_component_rejected() -> None:
    spec = get_spec("lesson")
    baseline = build_baseline_skeleton(spec, "standard", [])
    # Force a section to 4 components if needed
    section = max(baseline.sections, key=lambda s: len(s.components))
    while len(section.components) < 4:
        # Can't easily pad without allowed slugs — skip if already full path
        break
    if len(section.components) < 4:
        # Manually pad using allowed components
        allowed = list(spec.all_allowed_components_for_role(section.role))
        from v3_blueprint.planning.models import SkeletonComponent

        comps = list(section.components)
        for slug in allowed:
            if slug not in [c.slug for c in comps]:
                comps.append(SkeletonComponent(slug=slug))
            if len(comps) >= 4:
                break
        idx = baseline.sections.index(section)
        baseline.sections[idx] = section.model_copy(update={"components": comps[:4]})
        section = baseline.sections[idx]

    allowed = list(spec.all_allowed_components_for_role(section.role))
    extra = next(
        (slug for slug in allowed if slug not in [c.slug for c in section.components]),
        None,
    )
    if extra is None:
        return
    _, rejected = apply_edits(
        baseline,
        [AddComponent(section_id=section.id, slug=extra, reason="overflow")],
        spec,
        depth="standard",
    )
    assert rejected
    assert "4 components" in rejected[0].reason


def test_remove_missing_slug_rejected() -> None:
    spec = get_spec("lesson")
    baseline = build_baseline_skeleton(spec, "standard", [])
    section = baseline.sections[0]
    _, rejected = apply_edits(
        baseline,
        [
            RemoveComponent(
                section_id=section.id,
                slug="definitely-not-present-xyz",
                reason="test",
            )
        ],
        spec,
        depth="standard",
    )
    assert rejected


def test_set_visual_without_capable_component_rejected() -> None:
    spec = get_spec("exit_ticket")
    baseline = build_baseline_skeleton(spec, "standard", [])
    section = baseline.sections[0]
    _, rejected = apply_edits(
        baseline,
        [
            SetVisual(
                section_id=section.id,
                visual_required=True,
                reason="test",
            )
        ],
        spec,
        depth="standard",
    )
    assert rejected
