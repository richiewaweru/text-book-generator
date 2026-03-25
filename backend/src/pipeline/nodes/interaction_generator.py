"""
interaction_generator

Materializes a lightweight SimulationContent from the decided interaction spec.
"""

from __future__ import annotations

from pipeline.nodes.interaction_decider import build_interaction_spec
from pipeline.state import TextbookPipelineState
from pipeline.types.section_content import SimulationContent


async def interaction_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Materialize the deterministic simulation payload for the current section."""

    _ = model_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    section = state.generated_sections.get(sid)
    if sid is None or section is None:
        return {"completed_nodes": ["interaction_generator"]}

    composition = state.composition_plans.get(sid)
    if composition is not None and not composition.interaction.enabled:
        return {"completed_nodes": ["interaction_generator"]}

    spec = state.interaction_specs.get(sid)
    if spec is None:
        spec = build_interaction_spec(
            state,
            section,
            interaction_type=(
                composition.interaction.interaction_type
                if composition is not None
                else None
            ),
            anchor_block=(
                composition.interaction.anchor_block
                if composition is not None
                else None
            ),
        )
    if spec is None:
        return {"completed_nodes": ["interaction_generator"]}

    simulation = SimulationContent(
        spec=spec,
        fallback_diagram=section.diagram,
        explanation=(
            f"Interactive view for {section.header.title}. "
            f"Use it to test the key idea from this section step by step."
        ),
    )
    updated = section.model_copy(update={"simulation": simulation})
    generated = dict(state.generated_sections)
    generated[sid] = updated

    return {
        "interaction_specs": {sid: spec},
        "generated_sections": generated,
        "completed_nodes": ["interaction_generator"],
    }
