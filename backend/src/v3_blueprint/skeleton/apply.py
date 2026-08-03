"""
Apply bounded skeleton edits.

Section composition (which sections exist, and in what order) is fully
deterministic from the resource spec baseline. Edits may only change
components and visual_required flags within those sections. Illegal edits
are rejected and logged — never fatal, never silently applied.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.lectio import get_component_card
from resource_specs.schema import ResourceSpec
from v3_blueprint.planning.models import LessonSkeleton, SkeletonComponent, SkeletonSection
from v3_blueprint.skeleton.edits import (
    AddComponent,
    RemoveComponent,
    SetVisual,
    SkeletonEdit,
    SwapComponent,
)

_VISUAL_CAPABLE = {
    "diagram-block",
    "diagram-series",
    "diagram-compare",
    "worked-example-card",
    "timeline-block",
}


@dataclass(frozen=True)
class RejectedEdit:
    edit: SkeletonEdit
    reason: str
    role: str | None = None


def _section_field(slug: str) -> str | None:
    card = get_component_card(slug)
    if not card:
        return None
    field = card.get("sectionField") or card.get("section_field")
    return field if isinstance(field, str) else None


def _find_section(
    skeleton: LessonSkeleton,
    section_id: str,
) -> tuple[int, SkeletonSection] | None:
    for i, section in enumerate(skeleton.sections):
        if section.id == section_id:
            return i, section
    return None


def _fields_in_section(section: SkeletonSection) -> dict[str, str]:
    seen: dict[str, str] = {}
    for component in section.components:
        field = _section_field(component.slug)
        if isinstance(field, str):
            seen[field] = component.slug
    return seen


def apply_edits(
    baseline: LessonSkeleton,
    edits: list[SkeletonEdit],
    spec: ResourceSpec,
    *,
    generation_id: str | None = None,
    depth: str | None = None,
) -> tuple[LessonSkeleton, list[RejectedEdit]]:
    """
    Apply edits one at a time. Depth envelopes are read only from ``spec`` (I9).
    """
    current = baseline.model_copy(deep=True)
    rejected: list[RejectedEdit] = []

    # Envelopes from spec only — never from the edit plan (I9).
    max_sections = None
    visual_budget = None
    if depth is not None:
        depth_variant = spec.depth_limit(depth)
        max_sections = depth_variant.max_sections
        visual_budget = getattr(spec.visuals, depth, None)

    for edit in edits:
        ok, reason, role = _try_apply(current, edit, spec, visual_budget=visual_budget)
        if not ok:
            item = RejectedEdit(edit=edit, reason=reason, role=role)
            rejected.append(item)
            print(
                f"[SKELETON EDIT REJECTED] generation_id={generation_id}"
                f" edit={edit.kind} role={role} reason={reason}",
                flush=True,
            )
            continue

    if max_sections is not None and len(current.sections) > max_sections:
        # Edits cannot add sections; this is a defensive invariant check.
        pass

    return current, rejected


def _try_apply(
    skeleton: LessonSkeleton,
    edit: SkeletonEdit,
    spec: ResourceSpec,
    *,
    visual_budget: int | None,
) -> tuple[bool, str, str | None]:
    found = _find_section(skeleton, edit.section_id)
    if found is None:
        return False, f"unknown section_id '{edit.section_id}'", None
    index, section = found
    role = section.role

    if isinstance(edit, SwapComponent):
        return _swap(skeleton, index, section, edit, spec)
    if isinstance(edit, AddComponent):
        return _add(skeleton, index, section, edit, spec)
    if isinstance(edit, RemoveComponent):
        return _remove(skeleton, index, section, edit)
    if isinstance(edit, SetVisual):
        return _set_visual(skeleton, index, section, edit, visual_budget=visual_budget)
    return False, f"unsupported edit kind {type(edit)!r}", role


def _swap(
    skeleton: LessonSkeleton,
    index: int,
    section: SkeletonSection,
    edit: SwapComponent,
    spec: ResourceSpec,
) -> tuple[bool, str, str | None]:
    role = section.role
    slugs = [c.slug for c in section.components]
    if edit.from_slug not in slugs:
        return False, f"from_slug '{edit.from_slug}' not in section", role
    allowed = spec.all_allowed_components_for_role(role)
    forbidden = spec.forbidden_for_role(role)
    if edit.to_slug in forbidden or (allowed and edit.to_slug not in allowed):
        return False, f"to_slug '{edit.to_slug}' not allowed for role '{role}'", role
    to_field = _section_field(edit.to_slug)
    fields = _fields_in_section(section)
    from_field = _section_field(edit.from_slug)
    # Allow replacing the component that currently owns to_field.
    if to_field is not None and to_field in fields and fields[to_field] != edit.from_slug:
        return False, f"sectionField '{to_field}' collision", role
    new_components = []
    for component in section.components:
        if component.slug == edit.from_slug:
            new_components.append(SkeletonComponent(slug=edit.to_slug))
        else:
            new_components.append(component)
    skeleton.sections[index] = section.model_copy(update={"components": new_components})
    return True, "", role


def _add(
    skeleton: LessonSkeleton,
    index: int,
    section: SkeletonSection,
    edit: AddComponent,
    spec: ResourceSpec,
) -> tuple[bool, str, str | None]:
    role = section.role
    if len(section.components) >= 4:
        return False, "section already has 4 components", role
    if any(c.slug == edit.slug for c in section.components):
        return False, f"slug '{edit.slug}' already present", role
    allowed = spec.all_allowed_components_for_role(role)
    forbidden = spec.forbidden_for_role(role)
    if edit.slug in forbidden or (allowed and edit.slug not in allowed):
        return False, f"slug '{edit.slug}' not allowed for role '{role}'", role
    field = _section_field(edit.slug)
    if field is not None and field in _fields_in_section(section):
        return False, f"sectionField '{field}' collision", role
    updated = list(section.components) + [SkeletonComponent(slug=edit.slug)]
    skeleton.sections[index] = section.model_copy(update={"components": updated})
    return True, "", role


def _remove(
    skeleton: LessonSkeleton,
    index: int,
    section: SkeletonSection,
    edit: RemoveComponent,
) -> tuple[bool, str, str | None]:
    role = section.role
    if not any(c.slug == edit.slug for c in section.components):
        return False, f"slug '{edit.slug}' not in section", role
    updated = [c for c in section.components if c.slug != edit.slug]
    if not updated:
        return False, "cannot remove last component", role
    skeleton.sections[index] = section.model_copy(update={"components": updated})
    return True, "", role


def _set_visual(
    skeleton: LessonSkeleton,
    index: int,
    section: SkeletonSection,
    edit: SetVisual,
    *,
    visual_budget: int | None,
) -> tuple[bool, str, str | None]:
    role = section.role
    if edit.visual_required:
        slugs = {c.slug for c in section.components}
        if not slugs.intersection(_VISUAL_CAPABLE):
            return False, "no visual-capable component in section", role
        if visual_budget is not None:
            current = sum(1 for s in skeleton.sections if s.visual_required)
            if not section.visual_required and current >= visual_budget:
                return False, f"visual budget {visual_budget} exhausted", role
    skeleton.sections[index] = section.model_copy(
        update={"visual_required": edit.visual_required}
    )
    return True, "", role
