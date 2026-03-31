from __future__ import annotations

from pipeline.state import TextbookPipelineState
from pipeline.types.composition import CompositionPlan, DiagramPlan, InteractionPlan


def _has_simulation_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return "simulation-block" in components


def _has_diagram_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return bool({"diagram-block", "diagram-series", "diagram-compare"} & components)


def _diagram_allowed(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False
    if plan.diagram_policy == "disabled":
        return False
    if not _has_diagram_slot(state.contract):
        return False
    return plan.diagram_policy == "required" or bool(plan.needs_diagram)


def _interaction_allowed(state: TextbookPipelineState) -> bool:
    plan = state.current_section_plan
    if plan is None:
        return False
    if plan.interaction_policy == "disabled":
        return False
    if state.contract.interaction_level not in {"medium", "high"}:
        return False
    if not _has_simulation_slot(state.contract):
        return False
    return True


def _diagram_type(section) -> str:
    if section.process is not None:
        return "process"
    if section.timeline is not None:
        return "timeline"
    if section.comparison_grid is not None:
        return "comparison"
    return "concept_map"


def pick_interaction_type(state: TextbookPipelineState, section) -> str:
    """Canonical interaction type picker shared with interaction_decider."""
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


async def composition_planner(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"completed_nodes": ["composition_planner"]}

    plan = state.current_section_plan
    diagram_enabled = _diagram_allowed(state)
    interaction_enabled = _interaction_allowed(state)

    key_concepts = []
    if section.definition is not None:
        key_concepts.append(section.definition.term)
    key_concepts.extend(section.explanation.emphasis[:3])

    composition = CompositionPlan(
        diagram=DiagramPlan(
            enabled=diagram_enabled,
            reasoning=(
                "The reviewed section plan requires or strongly prefers a diagram."
                if diagram_enabled
                else "The reviewed section plan keeps this section text-first."
            ),
            diagram_type=_diagram_type(section) if diagram_enabled else None,
            focus_area="process" if section.process is not None else "explanation",
            key_concepts=key_concepts[:4],
            visual_guidance=(
                f"{plan.focus}. {plan.continuity_notes}"
                if plan is not None and plan.continuity_notes
                else plan.focus if plan is not None else None
            ),
        ),
        interaction=InteractionPlan(
            enabled=interaction_enabled,
            reasoning=(
                "The reviewed section plan allows an interaction for this section."
                if interaction_enabled
                else "This section should not add an interaction in the current plan."
            ),
            interaction_type=pick_interaction_type(state, section) if interaction_enabled else None,
            anchor_block=(
                "timeline"
                if section.timeline is not None
                else "worked_example"
                if section.worked_example is not None
                else "explanation"
            ),
        ),
    )

    return {
        "composition_plans": {sid: composition},
        "completed_nodes": ["composition_planner"],
    }
