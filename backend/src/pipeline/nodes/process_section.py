"""
Composite per-section node.

This wrapper runs the full per-section chain as a single unit so LangGraph
fan-out keeps each section's state isolated from the others.

Internally calls:
    content_generator -> diagram_generator -> interaction_decider
    -> interaction_generator -> section_assembler -> qc_agent
"""

from __future__ import annotations

from pipeline.nodes.content_generator import content_generator
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.interaction_decider import interaction_decider
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.qc_agent import qc_agent
from pipeline.nodes.section_assembler import section_assembler
from pipeline.nodes.section_runner import run_section_steps
from pipeline.state import TextbookPipelineState


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Run the full per-section pipeline chain and merge each step's outputs."""

    return await run_section_steps(
        state,
        steps=[
            ("content_generator", content_generator),
            ("diagram_generator", diagram_generator),
            ("interaction_decider", interaction_decider),
            ("interaction_generator", interaction_generator),
            ("section_assembler", section_assembler),
            ("qc_agent", qc_agent),
        ],
        model_overrides=model_overrides,
    )
