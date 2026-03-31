"""
Composite per-section node with explicit execution phases.

Phase 1: content_generator
Phase 2: composition_planner
Phase 3: diagram_generator || interaction_generator
Phase 4: section_assembler -> qc_agent
"""

from __future__ import annotations

from pipeline.nodes.composition_planner import composition_planner
from pipeline.nodes.content_generator import content_generator
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.interaction_decider import interaction_decider
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.qc_agent import qc_agent
from pipeline.nodes.section_assembler import section_assembler
from pipeline.nodes.section_runner import _run_parallel_phase, run_section_steps
from pipeline.state import TextbookPipelineState, merge_state_updates


async def _run_interaction_path(
    state: TextbookPipelineState,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Preserve the existing interaction_decider -> interaction_generator path."""

    return await run_section_steps(
        state,
        steps=[
            ("interaction_decider", interaction_decider),
            ("interaction_generator", interaction_generator),
        ],
        model_overrides=model_overrides,
    )


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Run the phased per-section pipeline and merge the step outputs."""

    typed = TextbookPipelineState.parse(state)

    phase1 = await run_section_steps(
        typed,
        steps=[("content_generator", content_generator)],
        model_overrides=model_overrides,
    )
    raw_state = typed.model_dump()
    merge_state_updates(raw_state, phase1)
    typed = TextbookPipelineState.parse(raw_state)
    if typed.current_section_id not in typed.generated_sections:
        return phase1

    phase2 = await run_section_steps(
        typed,
        steps=[("composition_planner", composition_planner)],
        model_overrides=model_overrides,
    )
    merge_state_updates(raw_state, phase2)
    typed = TextbookPipelineState.parse(raw_state)

    phase3 = await _run_parallel_phase(
        typed,
        steps=[
            ("diagram_generator", diagram_generator),
            ("interaction_path", _run_interaction_path),
        ],
        pre_instrumented=frozenset({"interaction_path"}),
        model_overrides=model_overrides,
    )
    merge_state_updates(raw_state, phase3)
    typed = TextbookPipelineState.parse(raw_state)

    phase4 = await run_section_steps(
        typed,
        steps=[
            ("section_assembler", section_assembler),
            ("qc_agent", qc_agent),
        ],
        model_overrides=model_overrides,
    )

    final_output: dict = {}
    for phase in (phase1, phase2, phase3, phase4):
        merge_state_updates(final_output, phase)
    return final_output
