"""Pure computed LessonSkeleton from ResourceSpec — no LLM, no I/O."""

from __future__ import annotations

from contracts.lectio import get_component_card
from resource_specs.schema import ResourceSpec, SectionSpec
from v3_blueprint.planning.models import (
    LessonSkeleton,
    SkeletonComponent,
    SkeletonSection,
)
from v3_blueprint.skeleton.support_applier import apply_support_modifications

_VISUAL_CAPABLE = {
    "diagram-block",
    "diagram-series",
    "diagram-compare",
    "worked-example-card",
    "timeline-block",
}


def _section_field(slug: str) -> str | None:
    card = get_component_card(slug)
    if not card:
        return None
    field = card.get("sectionField") or card.get("section_field")
    return field if isinstance(field, str) else None


def _components_for_section(spec: ResourceSpec, section: SectionSpec) -> list[SkeletonComponent]:
    forbidden = spec.forbidden_for_role(section.role)
    chosen: list[SkeletonComponent] = []
    seen_fields: set[str] = set()
    for slug in section.preferred_components:
        if slug in forbidden:
            continue
        field = _section_field(slug)
        if field is not None and field in seen_fields:
            continue
        chosen.append(SkeletonComponent(slug=slug))
        if field is not None:
            seen_fields.add(field)
        if len(chosen) >= 4:
            break
    return chosen


def _unique_section_id(role: str, used: dict[str, int]) -> str:
    count = used.get(role, 0)
    used[role] = count + 1
    if count == 0:
        return role
    return f"{role}_{count + 1}"


def _from_section_spec(
    spec: ResourceSpec,
    section: SectionSpec,
    used_ids: dict[str, int],
) -> SkeletonSection:
    return SkeletonSection(
        id=_unique_section_id(section.role, used_ids),
        title=section.role.replace("_", " ").title(),
        role=section.role,
        visual_required=False,
        components=_components_for_section(spec, section),
    )


def _assign_visuals(
    sections: list[SkeletonSection],
    budget: int,
) -> list[SkeletonSection]:
    if budget <= 0:
        return sections
    result = list(sections)
    assigned = 0
    for i, section in enumerate(result):
        if assigned >= budget:
            break
        slugs = {c.slug for c in section.components}
        if slugs.intersection(_VISUAL_CAPABLE):
            result[i] = section.model_copy(update={"visual_required": True})
            assigned += 1
    return result


def _trim_or_pad(
    sections: list[SkeletonSection],
    *,
    min_sections: int,
    max_sections: int,
    spec: ResourceSpec,
    used_ids: dict[str, int],
) -> list[SkeletonSection]:
    result = list(sections)
    if len(result) > max_sections:
        # Prefer dropping trailing optional-origin sections (not in required roles set
        # when duplicated beyond first occurrence of required roles). Truncate from end.
        result = result[:max_sections]
    while len(result) < min_sections and spec.sections.optional:
        # Pad toward min using first free optional that is not already present
        # when max_count allows.
        added = False
        for optional in spec.sections.optional:
            if optional.only_when_support:
                continue
            existing = sum(1 for s in result if s.role == optional.role)
            if existing >= optional.max_count:
                continue
            result.append(_from_section_spec(spec, optional, used_ids))
            added = True
            break
        if not added:
            break
    return result


def build_baseline_skeleton(
    spec: ResourceSpec,
    depth: str,
    active_supports: list[str],
    *,
    lesson_mode: str = "first_exposure",
    generation_id: str | None = None,
) -> LessonSkeleton:
    """
    Compute a legal LessonSkeleton from the resource spec.

    Order: required (YAML order) → support-gated optionals → SupportModification
    → min/max depth envelope → visual budget. Section composition is deterministic.
    """
    depth_variant = spec.depth_limit(depth)
    used_ids: dict[str, int] = {}
    sections: list[SkeletonSection] = [
        _from_section_spec(spec, section, used_ids)
        for section in spec.sections.required
    ]

    support_set = set(active_supports)
    for optional in spec.sections.optional:
        if optional.only_when_support and optional.only_when_support in support_set:
            existing = sum(1 for s in sections if s.role == optional.role)
            if existing < optional.max_count:
                sections.append(_from_section_spec(spec, optional, used_ids))

    sections = apply_support_modifications(sections, spec, active_supports)
    sections = _trim_or_pad(
        sections,
        min_sections=depth_variant.min_sections,
        max_sections=depth_variant.max_sections,
        spec=spec,
        used_ids=used_ids,
    )

    visual_budget = getattr(spec.visuals, depth, 0)
    if not isinstance(visual_budget, int):
        visual_budget = 0
    sections = _assign_visuals(sections, visual_budget)

    skeleton = LessonSkeleton(
        lesson_mode=lesson_mode,  # type: ignore[arg-type]
        sections=sections,
    )
    component_count = sum(len(s.components) for s in sections)
    print(
        f"[SKELETON BASELINE] generation_id={generation_id}"
        f" sections={len(sections)} components={component_count}"
        f" supports={active_supports}",
        flush=True,
    )
    return skeleton
