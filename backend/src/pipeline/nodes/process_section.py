"""
Graph-visible per-section flow helpers.

prepare_section
    content_generator -> composition_planner -> partial_section_assembler

generate_section_assets
    diagram_generator || image_generator || interaction_generator

finalize_section
    section_assembler -> qc_agent

process_section remains as a compatibility wrapper that runs the three phases
sequentially for tests and any narrow callers that still expect the old API.
"""

from __future__ import annotations

from datetime import datetime, timezone

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
from pipeline.section_assets import pending_visual_fields
from pipeline.state import PartialSectionRecord, TextbookPipelineState, merge_state_updates


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


async def _start_section_flow(
    state: TextbookPipelineState,
    *,
    config: RunnableConfig | None = None,
) -> tuple[object | None, bool]:
    runtime_context = get_runtime_context(config)
    section_id = state.current_section_id
    is_retry = section_id is not None and state.pending_rerender_for(section_id) is not None

    if runtime_context is not None and section_id is not None:
        await runtime_context.progress.queue_section(section_id)
        await runtime_context.limiters.section.acquire()
        await runtime_context.progress.start_section(section_id)
        if is_retry:
            await runtime_context.progress.start_retry(section_id)

    return runtime_context, is_retry


async def _finish_section_flow(
    runtime_context,
    *,
    section_id: str | None,
    is_retry: bool,
) -> None:
    if runtime_context is not None and section_id is not None:
        runtime_context.limiters.section.release()
        await runtime_context.progress.finish_section(section_id)
        if is_retry:
            await runtime_context.progress.finish_retry(section_id)


def _merge_phase_outputs(*phases: dict) -> dict:
    output: dict = {}
    for phase in phases:
        merge_state_updates(output, phase)
    return output


def _upsert_partial_record(
    state: TextbookPipelineState,
    *,
    pending_assets: list[str],
) -> dict[str, PartialSectionRecord]:
    section_id = state.current_section_id
    if section_id is None:
        return dict(state.partial_sections)

    section = state.generated_sections.get(section_id)
    partials = dict(state.partial_sections)
    if section is None:
        return partials

    partials[section_id] = PartialSectionRecord(
        section_id=section.section_id,
        template_id=section.template_id,
        content=section,
        status="awaiting_assets" if pending_assets else "partial",
        pending_assets=list(pending_assets),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    return partials


async def prepare_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    runtime_context, is_retry = await _start_section_flow(typed, config=config)
    continue_flow = False

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

        output = _merge_phase_outputs(phase1, phase2, phase3)
        pending_assets = phase3.get("section_pending_assets", {}).get(section_id, [])
        if pending_assets:
            output["_asset_pending"] = {section_id: list(pending_assets)}

        continue_flow = True
        return output
    finally:
        if not continue_flow:
            await _finish_section_flow(
                runtime_context,
                section_id=section_id,
                is_retry=is_retry,
            )


async def generate_section_assets(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    initial_pending_assets = list(typed.section_pending_assets.get(section_id, []))

    phase = await _run_parallel_phase(
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

    raw_state = typed.model_dump()
    merge_state_updates(raw_state, phase)
    updated = TextbookPipelineState.parse(raw_state)
    final_pending_assets = pending_visual_fields(updated)

    output = dict(phase)
    output["section_pending_assets"] = {section_id: list(final_pending_assets)}
    output["section_lifecycle"] = {
        section_id: "awaiting_assets" if final_pending_assets else "partial"
    }
    output["partial_sections"] = _upsert_partial_record(
        updated,
        pending_assets=final_pending_assets,
    )

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


async def finalize_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    section_id = typed.current_section_id
    runtime_context = get_runtime_context(config)
    is_retry = section_id is not None and typed.pending_rerender_for(section_id) is not None

    try:
        return await run_section_steps(
            typed,
            steps=[
                ("section_assembler", section_assembler),
                ("qc_agent", qc_agent),
            ],
            model_overrides=model_overrides,
            config=config,
        )
    finally:
        await _finish_section_flow(
            runtime_context,
            section_id=section_id,
            is_retry=is_retry,
        )


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    raw_state = typed.model_dump()

    phase1 = await prepare_section(
        typed,
        model_overrides=model_overrides,
        config=config,
    )
    merge_state_updates(raw_state, phase1)
    typed = TextbookPipelineState.parse(raw_state)
    if typed.current_section_id not in typed.generated_sections:
        return phase1

    phases = [phase1]
    if typed.section_pending_assets.get(typed.current_section_id):
        phase2 = await generate_section_assets(
            typed,
            model_overrides=model_overrides,
            config=config,
        )
        phases.append(phase2)
        merge_state_updates(raw_state, phase2)
        typed = TextbookPipelineState.parse(raw_state)

    phase3 = await finalize_section(
        typed,
        model_overrides=model_overrides,
        config=config,
    )
    phases.append(phase3)

    return _merge_phase_outputs(*phases)


__all__ = [
    "finalize_section",
    "generate_section_assets",
    "prepare_section",
    "process_section",
]
