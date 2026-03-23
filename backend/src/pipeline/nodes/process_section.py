"""
Composite per-section node.

This wrapper runs the full per-section chain as a single unit so LangGraph
fan-out keeps each section's state isolated from the others.

Internally calls:
    content_generator -> diagram_generator -> interaction_decider
    -> interaction_generator -> section_assembler
"""

from time import perf_counter

from pipeline.api import PipelineSectionReport
from pipeline.events import (
    NodeFinishedEvent,
    NodeStartedEvent,
    SectionAttemptStartedEvent,
    SectionReportUpdatedEvent,
)
from pipeline.nodes.content_generator import content_generator
from pipeline.nodes.diagram_generator import diagram_generator
from pipeline.nodes.interaction_decider import interaction_decider
from pipeline.nodes.interaction_generator import interaction_generator
from pipeline.nodes.section_assembler import section_assembler
from pipeline.runtime_diagnostics import (
    current_section_attempt,
    generation_id_from_state,
    node_error_messages,
    publish_runtime_event,
)
from pipeline.state import TextbookPipelineState


async def process_section(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
) -> dict:
    """Run the full per-section pipeline chain and merge each step's outputs."""

    typed = TextbookPipelineState.parse(state)
    raw = typed.model_dump()
    sid = typed.current_section_id
    generation_id = generation_id_from_state(typed)
    attempt, trigger = current_section_attempt(typed, sid)

    if generation_id and sid and attempt is not None:
        publish_runtime_event(
            generation_id,
            SectionAttemptStartedEvent(
                generation_id=generation_id,
                section_id=sid,
                attempt=attempt,
                trigger=trigger,
            ),
        )

    # Thread the running state through each step so later stages see the latest
    # generated content, diagrams, interaction specs, and QC data.
    for step in [
        content_generator,
        diagram_generator,
        interaction_decider,
        interaction_generator,
        section_assembler,
    ]:
        node_name = step.__name__
        step_started = perf_counter()
        if generation_id:
            publish_runtime_event(
                generation_id,
                NodeStartedEvent(
                    generation_id=generation_id,
                    node=node_name,
                    section_id=sid,
                    attempt=attempt,
                ),
            )

        try:
            result = await step(raw, model_overrides=model_overrides)
        except Exception as exc:
            publish_runtime_event(
                generation_id,
                NodeFinishedEvent(
                    generation_id=generation_id,
                    node=node_name,
                    section_id=sid,
                    attempt=attempt,
                    status="failed",
                    latency_ms=(perf_counter() - step_started) * 1000.0,
                    error=str(exc),
                ),
            )
            raise

        for key, value in result.items():
            if isinstance(value, dict) and isinstance(raw.get(key), dict):
                raw[key] = {**raw[key], **value}
            elif isinstance(value, list) and isinstance(raw.get(key), list):
                raw[key] = raw[key] + value
            else:
                raw[key] = value

        step_errors = node_error_messages(
            result.get("errors"),
            node=node_name,
            section_id=sid,
        )
        publish_runtime_event(
            generation_id,
            NodeFinishedEvent(
                generation_id=generation_id,
                node=node_name,
                section_id=sid,
                attempt=attempt,
                status="failed" if step_errors else "succeeded",
                latency_ms=(perf_counter() - step_started) * 1000.0,
                error=" | ".join(step_errors) if step_errors else None,
            ),
        )

        if (
            node_name == "section_assembler"
            and generation_id
            and sid
            and sid in result.get("qc_reports", {})
        ):
            publish_runtime_event(
                generation_id,
                SectionReportUpdatedEvent(
                    generation_id=generation_id,
                    section_id=sid,
                    source="assembler",
                    report=PipelineSectionReport.model_validate(
                        result["qc_reports"][sid]
                    ),
                ),
            )

    typed_final = TextbookPipelineState.parse(raw)

    output: dict = {
        "completed_nodes": [
            "content_generator",
            "diagram_generator",
            "interaction_decider",
            "interaction_generator",
            "section_assembler",
        ],
    }

    # Return only the current section's output so fan-out branches stay isolated.
    if sid and sid in typed_final.generated_sections:
        output["generated_sections"] = {sid: typed_final.generated_sections[sid]}
    if sid and sid in typed_final.assembled_sections:
        output["assembled_sections"] = {sid: typed_final.assembled_sections[sid]}
    if sid and sid in typed_final.interaction_specs:
        output["interaction_specs"] = {sid: typed_final.interaction_specs[sid]}
    if sid and sid in typed_final.qc_reports:
        output["qc_reports"] = {sid: typed_final.qc_reports[sid]}

    new_errors = typed_final.errors[len(typed.errors) :]
    if new_errors:
        output["errors"] = new_errors

    return output
