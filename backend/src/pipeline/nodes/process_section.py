"""
Composite per-section node with explicit execution phases.

Phase 1: content_generator
Phase 2: composition_planner
Phase 3: partial_section_assembler
Phase 4: diagram_generator || image_generator || interaction_generator
Phase 5: section_assembler -> qc_agent
"""

from __future__ import annotations

from langchain_core.runnables.config import RunnableConfig

from pipeline.nodes.composition_planner import composition_planner
from pipeline.nodes.content_generator import content_generator
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.image_generator import image_generator
from pipeline.nodes.interaction_decider import interaction_decider
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.qc_agent import qc_agent
from pipeline.nodes.section_assembler import partial_section_assembler, section_assembler
from pipeline.nodes.section_runner import _run_parallel_phase, run_section_steps
from pipeline.runtime_context import get_runtime_context
from pipeline.state import TextbookPipelineState, merge_state_updates


async def _run_interaction_path(
    state: TextbookPipelineState,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    return await run_section_steps(
        state,
        steps=[
            ("interaction_decider", interaction_decider),
            ("interaction_generator", interaction_generator),
        ],
        model_overrides=model_overrides,
        config=config,
    )


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    runtime_context = get_runtime_context(config)
    section_id = typed.current_section_id
    is_retry = section_id is not None and typed.pending_rerender_for(section_id) is not None

    if runtime_context is not None and section_id is not None:
        await runtime_context.progress.queue_section(section_id)
        await runtime_context.limiters.section.acquire()
        await runtime_context.progress.start_section(section_id)
        if is_retry:
            await runtime_context.progress.start_retry(section_id)

    try:
        phase1 = await run_section_steps(
            typed,
            steps=[("content_generator", content_generator)],
            model_overrides=model_overrides,
            config=config,
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
            config=config,
        )
        merge_state_updates(raw_state, phase2)
        typed = TextbookPipelineState.parse(raw_state)

        phase3 = await run_section_steps(
            typed,
            steps=[("partial_section_assembler", partial_section_assembler)],
            model_overrides=model_overrides,
            config=config,
        )
        merge_state_updates(raw_state, phase3)
        typed = TextbookPipelineState.parse(raw_state)

        phase4 = await _run_parallel_phase(
            typed,
            steps=[
                ("diagram_generator", diagram_generator),
                ("image_generator", image_generator),
                ("interaction_path", _run_interaction_path),
            ],
            pre_instrumented=frozenset({"interaction_path"}),
            model_overrides=model_overrides,
            config=config,
        )
        merge_state_updates(raw_state, phase4)
        typed = TextbookPipelineState.parse(raw_state)

        phase5 = await run_section_steps(
            typed,
            steps=[
                ("section_assembler", section_assembler),
                ("qc_agent", qc_agent),
            ],
            model_overrides=model_overrides,
            config=config,
        )

        output: dict = {}
        for phase in (phase1, phase2, phase3, phase4, phase5):
            merge_state_updates(output, phase)

        initial_pending_assets = phase3.get("section_pending_assets", {}).get(section_id, [])
        final_pending_assets = phase5.get("section_pending_assets", {}).get(
            section_id,
            phase4.get("section_pending_assets", {}).get(section_id, initial_pending_assets),
        )
        if initial_pending_assets:
            output["_asset_pending"] = {section_id: list(initial_pending_assets)}
            ready_assets = [
                asset
                for asset in initial_pending_assets
                if asset not in set(final_pending_assets)
            ]
            if ready_assets:
                output["_asset_ready"] = {
                    section_id: {
                        "ready_assets": ready_assets,
                        "pending_assets": list(final_pending_assets),
                    }
                }

        return output
    finally:
        if runtime_context is not None and section_id is not None:
            runtime_context.limiters.section.release()
            await runtime_context.progress.finish_section(section_id)
            if is_retry:
                await runtime_context.progress.finish_retry(section_id)
