"""
Composite per-section node. Runs the full per-section chain as a single unit
so that LangGraph's Send fan-out keeps each section's context isolated.

Internally calls: content_generator → diagram_generator → interaction_decider
                  → interaction_generator → section_assembler
"""

from pipeline.nodes.content_generator import content_generator
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.interaction_decider import interaction_decider
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.section_assembler import section_assembler
from pipeline.state import TextbookPipelineState


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    provider_overrides: dict | None = None,
) -> dict:
    """Run all per-section steps in sequence, return merged outputs."""
    typed = TextbookPipelineState.parse(state)
    raw = typed.model_dump()

    # Run each step, merging results into the running state dict
    for step in [
        content_generator,
        diagram_generator,
        interaction_decider,
        interaction_generator,
        section_assembler,
    ]:
        result = await step(raw, provider_overrides=provider_overrides)
        # Merge step output into running state so next step sees it
        for key, value in result.items():
            if isinstance(value, dict) and isinstance(raw.get(key), dict):
                raw[key] = {**raw[key], **value}
            elif isinstance(value, list) and isinstance(raw.get(key), list):
                raw[key] = raw[key] + value
            else:
                raw[key] = value

    # Return only the fields that changed (outputs from all sub-steps)
    typed_final = TextbookPipelineState.parse(raw)
    sid = typed.current_section_id

    output: dict = {
        "completed_nodes": [
            "content_generator", "diagram_generator",
            "interaction_decider", "interaction_generator",
            "section_assembler",
        ],
    }

    # Only return the current section's data
    if sid and sid in typed_final.generated_sections:
        output["generated_sections"] = {sid: typed_final.generated_sections[sid]}
    if sid and sid in typed_final.assembled_sections:
        output["assembled_sections"] = {sid: typed_final.assembled_sections[sid]}
    if sid and sid in typed_final.interaction_specs:
        output["interaction_specs"] = {sid: typed_final.interaction_specs[sid]}
    if sid and sid in typed_final.qc_reports:
        output["qc_reports"] = {sid: typed_final.qc_reports[sid]}

    # Forward any errors
    new_errors = typed_final.errors[len(typed.errors):]
    if new_errors:
        output["errors"] = new_errors

    return output
