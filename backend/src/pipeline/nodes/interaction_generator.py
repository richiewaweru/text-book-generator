"""
interaction_generator

Materializes a lightweight SimulationContent from the decided interaction spec.
"""

from __future__ import annotations

from pipeline.state import TextbookPipelineState
from pipeline.types.section_content import SimulationContent


async def interaction_generator(
    state: TextbookPipelineState | dict,
    *,
    provider_overrides: dict | None = None,
) -> dict:
    _ = provider_overrides
    state = TextbookPipelineState.parse(state)
    sid = state.current_section_id
    spec = state.interaction_specs.get(sid)

    if not spec:
        return {"completed_nodes": ["interaction_generator"]}

    section = state.generated_sections.get(sid)
    if section is None:
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
        "generated_sections": generated,
        "completed_nodes": ["interaction_generator"],
    }
