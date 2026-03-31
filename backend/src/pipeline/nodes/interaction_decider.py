"""
interaction_decider

Creates an interaction spec when the current template can support one and the
generation mode allows interaction work.
"""

from __future__ import annotations

from pipeline.nodes.composition_planner import pick_interaction_type
from pipeline.state import TextbookPipelineState
from pipeline.types.section_content import InteractionSpec


def _has_simulation_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return "simulation-block" in components


def build_interaction_spec(
    state: TextbookPipelineState,
    section,
    *,
    interaction_type: str | None = None,
    anchor_block: str | None = None,
) -> InteractionSpec | None:
    plan = state.current_section_plan
    if plan is not None and plan.interaction_policy == "disabled":
        return None
    if state.contract.interaction_level not in {"medium", "high"}:
        return None
    if not _has_simulation_slot(state.contract):
        return None

    return InteractionSpec(
        type=interaction_type or pick_interaction_type(state, section),
        goal=section.header.objective or section.hook.headline,
        anchor_content={
            "headline": section.hook.headline,
            "body": section.explanation.body[:280],
        },
        context={
            "subject": state.request.subject,
            "grade_band": state.request.grade_band,
            "section_title": section.header.title,
            "anchor_block": anchor_block or "explanation",
        },
        dimensions={
            "difficulty": "standard",
            "interaction_level": state.contract.interaction_level,
        },
        print_translation="static_diagram",
    )


async def interaction_decider(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Choose a deterministic interaction type when the template supports it."""

    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    plan = state.current_section_plan

    if plan is not None and plan.interaction_policy == "disabled":
        return {"completed_nodes": ["interaction_decider"]}

    if state.contract.interaction_level not in {"medium", "high"}:
        return {"completed_nodes": ["interaction_decider"]}
    if not _has_simulation_slot(state.contract):
        return {"completed_nodes": ["interaction_decider"]}

    section = state.generated_sections.get(sid)
    if section is None:
        return {"completed_nodes": ["interaction_decider"]}

    spec = build_interaction_spec(state, section)
    if spec is None:
        return {"completed_nodes": ["interaction_decider"]}

    return {
        "interaction_specs": {sid: spec},
        "completed_nodes": ["interaction_decider"],
    }
