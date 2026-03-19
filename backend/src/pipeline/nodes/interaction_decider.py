"""
interaction_decider

Creates an interaction spec when the current template can support one and the
generation mode allows interaction work.
"""

from __future__ import annotations

from pipeline.state import TextbookPipelineState
from pipeline.types.section_content import InteractionSpec


def _has_simulation_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return "simulation-block" in components


def _pick_simulation_type(state: TextbookPipelineState, section) -> str:
    subject = state.request.subject.lower()
    if section.timeline is not None or "history" in subject:
        return "timeline_scrubber"
    if section.process is not None:
        return "equation_reveal"
    if section.diagram is not None and ("geometry" in subject or "physics" in subject):
        return "geometry_explorer"
    if "probability" in subject:
        return "probability_tree"
    return "graph_slider"


async def interaction_decider(
    state: TextbookPipelineState | dict,
    *,
    provider_overrides: dict | None = None,
) -> dict:
    _ = provider_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id

    if not state.request.interactions_enabled():
        return {"completed_nodes": ["interaction_decider"]}
    if state.contract.interaction_level not in {"medium", "high"}:
        return {"completed_nodes": ["interaction_decider"]}
    if not _has_simulation_slot(state.contract):
        return {"completed_nodes": ["interaction_decider"]}

    section = state.generated_sections.get(sid)
    if section is None:
        return {"completed_nodes": ["interaction_decider"]}

    spec = InteractionSpec(
        type=_pick_simulation_type(state, section),
        goal=section.header.objective or section.hook.headline,
        anchor_content={
            "headline": section.hook.headline,
            "body": section.explanation.body[:280],
        },
        context={
            "subject": state.request.subject,
            "grade_band": state.request.grade_band,
            "section_title": section.header.title,
        },
        dimensions={
            "difficulty": state.request.mode.value,
            "interaction_level": state.contract.interaction_level,
        },
        print_translation="static_diagram",
    )

    return {
        "interaction_specs": {sid: spec},
        "completed_nodes": ["interaction_decider"],
    }
