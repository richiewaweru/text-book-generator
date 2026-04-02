"""
interaction_generator node.

Generates 0-N SimulationContent blocks from the composition plan's
interactions list. Deterministic (no LLM call).

STATE CONTRACT:
    Reads:  current_section_id, composition_plans, generated_sections, request, contract
    Writes: generated_sections[id].simulation, generated_sections[id].simulations,
            interaction_specs, completed_nodes
"""

from __future__ import annotations

from pipeline.nodes.composition_planner import pick_interaction_type
from pipeline.state import TextbookPipelineState
from pipeline.types.composition import InteractionPlan
from pipeline.types.section_content import InteractionSpec, SimulationContent


def _has_simulation_slot(contract) -> bool:
    components = set(contract.required_components) | set(contract.optional_components)
    return "simulation-block" in components


def _build_interaction_spec(
    state: TextbookPipelineState,
    section,
    plan: InteractionPlan,
) -> InteractionSpec | None:
    """Build an InteractionSpec from an InteractionPlan and section context."""
    section_plan = state.current_section_plan
    if section_plan is not None and section_plan.interaction_policy == "disabled":
        return None
    if state.contract.interaction_level not in {"medium", "high"}:
        return None
    if not _has_simulation_slot(state.contract):
        return None

    interaction_type = plan.interaction_type or pick_interaction_type(state, section)

    anchor_content = {
        "headline": section.hook.headline,
        "body": section.explanation.body[:280],
    }
    if plan.manipulable_element:
        anchor_content["manipulable"] = plan.manipulable_element
    if plan.response_element:
        anchor_content["response"] = plan.response_element

    return InteractionSpec(
        type=interaction_type,
        goal=plan.pedagogical_payoff or section.header.objective or section.hook.headline,
        anchor_content=anchor_content,
        context={
            "subject": state.request.subject,
            "grade_band": state.request.grade_band,
            "section_title": section.header.title,
            "anchor_block": plan.anchor_block or "explanation",
        },
        dimensions={
            "difficulty": "standard",
            "interaction_level": state.contract.interaction_level,
            "complexity": plan.complexity,
            "estimated_time": plan.estimated_time_minutes,
        },
        print_translation="static_diagram",
    )


# Keep the old name available for backward compat (used by interaction_decider shim)
build_interaction_spec = _build_interaction_spec


async def interaction_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Generate simulation content for enabled interactions.

    Supports multiple interactions per section from the composition plan.
    Falls back to the singular `interaction` field if `interactions` list is empty.
    """

    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"completed_nodes": ["interaction_generator"]}

    composition = state.composition_plans.get(sid)
    if composition is None:
        return {"completed_nodes": ["interaction_generator"]}

    # Gather interaction plans: prefer list, fall back to singular
    interaction_plans = composition.interactions
    if not interaction_plans and composition.interaction.enabled:
        interaction_plans = [composition.interaction]

    # Filter to enabled only
    enabled_plans = [p for p in interaction_plans if p.enabled]
    if not enabled_plans:
        return {"completed_nodes": ["interaction_generator"]}

    # Build SimulationContent for each enabled plan
    simulations: list[SimulationContent] = []
    first_spec: InteractionSpec | None = None

    for plan in enabled_plans:
        spec = _build_interaction_spec(state, section, plan)
        if spec is None:
            continue

        if first_spec is None:
            first_spec = spec

        simulation = SimulationContent(
            spec=spec,
            fallback_diagram=section.diagram,
            explanation=(
                plan.reasoning
                if plan.reasoning
                else f"Interactive view for {section.header.title}. "
                     f"Use it to test the key idea from this section step by step."
            ),
        )
        simulations.append(simulation)

    if not simulations:
        return {"completed_nodes": ["interaction_generator"]}

    # Update section with both singular (backward compat) and plural fields
    updated = section.model_copy(update={
        "simulation": simulations[0],
        "simulations": simulations,
    })
    generated = dict(state.generated_sections)
    generated[sid] = updated

    result: dict = {
        "generated_sections": generated,
        "completed_nodes": ["interaction_generator"],
    }

    # Backward compat: populate interaction_specs for retry path
    if first_spec is not None:
        result["interaction_specs"] = {sid: first_spec}

    return result
