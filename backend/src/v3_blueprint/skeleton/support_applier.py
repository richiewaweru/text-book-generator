"""Apply SupportModification dict shapes from shipped resource spec YAML."""

from __future__ import annotations

from resource_specs.schema import ResourceSpec, SupportModification
from v3_blueprint.planning.models import SkeletonComponent, SkeletonSection


def _max_count_for_role(spec: ResourceSpec, role: str) -> int:
    for section in [*spec.sections.required, *spec.sections.optional]:
        if section.role == role:
            return section.max_count
    return 1


def _placement_index(sections: list[SkeletonSection], placement: str | None) -> int:
    """Map free-text placement hints to an insertion index; default append."""
    if not placement:
        return len(sections)
    token = placement.strip().lower().replace("-", "_")
    if token.startswith("before_"):
        target = token.removeprefix("before_")
        for i, section in enumerate(sections):
            if section.role == target:
                return i
    if token.startswith("after_"):
        target = token.removeprefix("after_")
        for i, section in enumerate(sections):
            if section.role == target:
                return i + 1
    return len(sections)


def _section_from_adds_section(payload: dict, *, section_id: str) -> SkeletonSection:
    role = str(payload.get("role") or "section")
    preferred = payload.get("preferred_components") or []
    if not isinstance(preferred, list):
        preferred = []
    components = [
        SkeletonComponent(slug=str(slug))
        for slug in preferred[:4]
        if isinstance(slug, str) and slug
    ]
    return SkeletonSection(
        id=section_id,
        title=role.replace("_", " ").title(),
        role=role,
        visual_required=False,
        components=components,
    )


def apply_support_modifications(
    sections: list[SkeletonSection],
    spec: ResourceSpec,
    active_supports: list[str],
) -> list[SkeletonSection]:
    result = list(sections)
    for support_key in active_supports:
        mod = spec.supports.get(support_key)
        if mod is None:
            continue
        result = _apply_one(result, spec, mod)
    return result


def _apply_one(
    sections: list[SkeletonSection],
    spec: ResourceSpec,
    mod: SupportModification,
) -> list[SkeletonSection]:
    result = list(sections)

    if mod.ensures_role and not any(s.role == mod.ensures_role for s in result):
        preferred = list(mod.preferred_components)[:4]
        new_section = SkeletonSection(
            id=mod.ensures_role,
            title=mod.ensures_role.replace("_", " ").title(),
            role=mod.ensures_role,
            visual_required=mod.ensures_role == "visual",
            components=[SkeletonComponent(slug=slug) for slug in preferred],
        )
        result.insert(_placement_index(result, mod.placement), new_section)

    if mod.adds_section and isinstance(mod.adds_section, dict):
        role = str(mod.adds_section.get("role") or "")
        existing = sum(1 for s in result if s.role == role) if role else 0
        if role and existing < _max_count_for_role(spec, role):
            placement = mod.adds_section.get("placement")
            if not isinstance(placement, str):
                placement = mod.placement
            section_id = role if existing == 0 else f"{role}_{existing + 1}"
            new_section = _section_from_adds_section(
                mod.adds_section,
                section_id=section_id,
            )
            result.insert(_placement_index(result, placement), new_section)

    if mod.adds_component and isinstance(mod.adds_component, dict):
        to_role = mod.adds_component.get("to_role")
        component = mod.adds_component.get("component")
        if isinstance(to_role, str) and isinstance(component, str):
            result = _ensure_component_on_role(result, to_role, component)

    if mod.ensures_component and isinstance(mod.ensures_component, dict):
        in_role = mod.ensures_component.get("in_role")
        component = mod.ensures_component.get("component")
        if isinstance(in_role, str) and isinstance(component, str):
            result = _ensure_component_on_role(result, in_role, component)

    return result


def _ensure_component_on_role(
    sections: list[SkeletonSection],
    role: str,
    component: str,
) -> list[SkeletonSection]:
    result = list(sections)
    for i, section in enumerate(result):
        if section.role != role:
            continue
        slugs = [c.slug for c in section.components]
        if component not in slugs and len(section.components) < 4:
            updated = list(section.components) + [SkeletonComponent(slug=component)]
            result[i] = section.model_copy(update={"components": updated})
        break
    return result
