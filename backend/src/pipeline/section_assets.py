from __future__ import annotations

from pipeline.state import TextbookPipelineState
from pipeline.visual_resolution import (
    pending_visual_fields as resolve_pending_visual_fields,
    required_visual_fields as resolve_required_visual_fields,
)

_VISUAL_FIELDS = {"diagram", "diagram_compare", "diagram_series"}


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
    return _dedupe_preserve_order(resolve_required_visual_fields(state))


def pending_visual_fields(state: TextbookPipelineState) -> list[str]:
    return _dedupe_preserve_order(resolve_pending_visual_fields(state))


def is_required_visual_block(state: TextbookPipelineState, block_type: str | None) -> bool:
    if not block_type:
        return False
    return block_type in _VISUAL_FIELDS and block_type in set(required_visual_fields(state))
