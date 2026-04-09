from __future__ import annotations

from pipeline.state import TextbookPipelineState

_VISUAL_COMPONENT_TO_FIELD = {
    "diagram-block": "diagram",
    "diagram-compare": "diagram_compare",
    "diagram-series": "diagram_series",
}
_VISUAL_FIELDS = set(_VISUAL_COMPONENT_TO_FIELD.values())


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _requires_visual_from_plan(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False
    if plan.diagram_policy == "required":
        return True
    visual_policy = getattr(plan, "visual_policy", None)
    return bool(visual_policy is not None and visual_policy.required)


def required_visual_fields(state: TextbookPipelineState) -> list[str]:
    plan = state.current_section_plan
    candidates: list[str] = []

    if plan is not None:
        candidates.extend(plan.required_components)
    candidates.extend(state.contract.required_components)

    mapped = [
        _VISUAL_COMPONENT_TO_FIELD[component_id]
        for component_id in candidates
        if component_id in _VISUAL_COMPONENT_TO_FIELD
    ]
    if mapped:
        return _dedupe_preserve_order(mapped)

    if not _requires_visual_from_plan(state):
        return []

    available = set(state.contract.required_components) | set(state.contract.optional_components)
    for component_id in ("diagram-series", "diagram-compare", "diagram-block"):
        if component_id in available:
            return [_VISUAL_COMPONENT_TO_FIELD[component_id]]
    return ["diagram"]


def pending_visual_fields(state: TextbookPipelineState) -> list[str]:
    section_id = state.current_section_id
    if section_id is None:
        return []
    section = state.generated_sections.get(section_id)
    if section is None:
        return []

    payload = section.model_dump(exclude_none=True)
    return [
        field_name
        for field_name in required_visual_fields(state)
        if not payload.get(field_name)
    ]


def is_required_visual_block(state: TextbookPipelineState, block_type: str | None) -> bool:
    if not block_type:
        return False
    return block_type in _VISUAL_FIELDS and block_type in set(required_visual_fields(state))

