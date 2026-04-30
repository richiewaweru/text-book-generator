from __future__ import annotations

import asyncio
from importlib import import_module

from langchain_core.runnables.config import RunnableConfig

from pipeline.media.assembly import (
    apply_slot_results_to_section,
    build_slot_result,
    frame_has_required_artifact,
    frame_result_key,
)
from pipeline.media.svg_sanitizer import SvgSanitizationError
from pipeline.media.svg_validator import SvgIntentValidationError, SvgValidationError
from pipeline.media.runtime_events import (
    emit_frame_failed,
    emit_frame_ready,
    emit_frame_started,
    emit_slot_state,
)
from pipeline.media.types import (
    SlotType,
    VisualFrameResult,
    VisualFrameResultStatus,
)
from pipeline.section_content_helpers import section_title
from pipeline.state import PipelineError, TextbookPipelineState


def _svg_generation_mode(legacy) -> str:
    return "raw_svg" if legacy._raw_svg_diagrams_enabled() else "legacy_spec"


def _svg_failure_reason(exc: Exception) -> str:
    if isinstance(exc, SvgSanitizationError):
        return "sanitizer"
    if isinstance(exc, SvgIntentValidationError):
        return "intent"
    if isinstance(exc, SvgValidationError):
        return "validation"
    return "generation"


def _static_svg_slots(state: TextbookPipelineState) -> list:
    media_plan = state.media_plans.get(state.current_section_id)
    if media_plan is None:
        return []
    return [
        slot
        for slot in media_plan.slots
        if slot.slot_type in {SlotType.DIAGRAM, SlotType.DIAGRAM_COMPARE, SlotType.DIAGRAM_SERIES}
        and slot.preferred_render.value == "svg"
    ]


def _previous_steps_context(slot, frame, slot_frame_results: dict[str, VisualFrameResult]) -> str | None:
    if slot.slot_type != SlotType.DIAGRAM_SERIES:
        return None

    lines: list[str] = []
    current_key = frame_result_key(frame)
    for previous_frame in slot.frames:
        if frame_result_key(previous_frame) == current_key:
            break
        previous_result = slot_frame_results.get(frame_result_key(previous_frame))
        if not frame_has_required_artifact(slot, previous_result):
            continue

        label = previous_result.label or previous_frame.label or f"Step {previous_frame.index + 1}"
        details: list[str] = []
        if previous_result.diagram_kind:
            details.append(f"diagram kind: {previous_result.diagram_kind}")
        if previous_result.explanation:
            details.append(f"caption: {previous_result.explanation}")
        if previous_result.generation_notes:
            details.append(f"self-check: {'; '.join(previous_result.generation_notes)}")
        summary = "; ".join(details) if details else "generated successfully"
        lines.append(f"Step {previous_frame.index + 1} ({label}): {summary}")

    if not lines:
        return None
    return "\n".join(lines)


def _previous_attempt_feedback(
    *,
    frame,
    retry_request,
    slot_frame_results: dict[str, VisualFrameResult],
) -> str | None:
    if retry_request is None or retry_request.frame_key != frame_result_key(frame):
        return None

    previous_result = slot_frame_results.get(frame_result_key(frame))
    if previous_result is None:
        return retry_request.reason

    parts: list[str] = []
    if previous_result.svg_failure_reason:
        parts.append(f"failure category: {previous_result.svg_failure_reason}")
    if previous_result.error_message:
        parts.append(previous_result.error_message)
    elif retry_request.reason:
        parts.append(retry_request.reason)
    return "\n".join(parts) if parts else None


def _frame_with_prompt_context(
    *,
    slot,
    frame,
    retry_request,
    slot_frame_results: dict[str, VisualFrameResult],
):
    updates: dict[str, str | None] = {}
    previous_steps = _previous_steps_context(slot, frame, slot_frame_results)
    if previous_steps:
        updates["previous_steps_context"] = previous_steps
    previous_feedback = _previous_attempt_feedback(
        frame=frame,
        retry_request=retry_request,
        slot_frame_results=slot_frame_results,
    )
    if previous_feedback:
        updates["previous_attempt_feedback"] = previous_feedback

    if not updates:
        return frame
    return frame.model_copy(
        update={
            "output_placeholders": {
                **frame.output_placeholders,
                **updates,
            }
        }
    )


async def _generate_frame(
    *,
    legacy,
    state: TextbookPipelineState,
    slot,
    frame,
    section_title: str,
    model_overrides: dict | None,
    config: RunnableConfig | None,
) -> VisualFrameResult:
    output = await legacy._generate_diagram_svg_output(
        state,
        slot=slot,
        frame=frame,
        section_title=section_title,
        model_overrides=model_overrides,
        config=config,
    )
    return VisualFrameResult(
        slot_id=slot.slot_id,
        frame_index=frame.index,
        label=frame.label,
        render=slot.preferred_render,
        status=VisualFrameResultStatus.GENERATED,
        svg_content=output.svg_content,
        svg_generation_mode=_svg_generation_mode(legacy),
        model_slot="standard",
        diagram_kind=output.diagram_kind,
        generation_notes=output.self_check,
        sanitized=legacy._raw_svg_diagrams_enabled(),
        intent_validated=legacy._raw_svg_diagrams_enabled(),
        alt_text=output.alt_text,
        explanation=output.caption,
    )


async def diagram_generator(
    state: TextbookPipelineState | dict,
    *,
    model_overrides: dict | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    typed = TextbookPipelineState.parse(state)
    legacy = import_module("pipeline.nodes.diagram_generator")
    sid = typed.current_section_id
    section = typed.generated_sections.get(sid)
    generation_id = typed.request.generation_id or ""
    outcomes = dict(typed.diagram_outcomes)

    if sid is None or section is None:
        return {"completed_nodes": ["diagram_generator"]}

    slots = _static_svg_slots(typed)
    retry_request = typed.pending_media_retry_for(sid)
    if retry_request is not None and retry_request.executor_node != "diagram_generator":
        return {"completed_nodes": ["diagram_generator"]}
    if retry_request is not None:
        slots = [slot for slot in slots if slot.slot_id == retry_request.slot_id]

    if not slots:
        outcomes = legacy._with_outcome(
            outcomes,
            generation_id=generation_id,
            section_id=sid,
            outcome="skipped",
        )
        return {"diagram_outcomes": outcomes, "completed_nodes": ["diagram_generator"]}

    if typed.style_context is None:
        outcomes = legacy._with_outcome(
            outcomes,
            generation_id=generation_id,
            section_id=sid,
            outcome="error",
        )
        return {
            "errors": [
                PipelineError(
                    node="diagram_generator",
                    section_id=sid,
                    message="style_context is None -- curriculum_planner may have failed",
                    recoverable=False,
                )
            ],
            "diagram_outcomes": outcomes,
            "completed_nodes": ["diagram_generator"],
        }

    updated_section = section
    section_slot_results = dict(typed.media_slot_results.get(sid, {}))
    section_frame_results = {
        slot_id: dict(frame_results)
        for slot_id, frame_results in typed.media_frame_results.get(sid, {}).items()
    }
    errors: list[PipelineError] = []
    saw_timeout = False

    for slot in slots:
        current_title = section_title(updated_section)
        slot_frame_results = dict(section_frame_results.get(slot.slot_id, {}))
        target_frames = slot.frames
        if retry_request is not None:
            target_frames = [
                frame for frame in slot.frames if frame_result_key(frame) == retry_request.frame_key
            ]

        for frame in target_frames:
            frame_for_generation = _frame_with_prompt_context(
                slot=slot,
                frame=frame,
                retry_request=retry_request,
                slot_frame_results=slot_frame_results,
            )
            emit_frame_started(
                generation_id=generation_id,
                section_id=sid,
                slot=slot,
                frame=frame_for_generation,
            )
            try:
                generated_frame = await _generate_frame(
                    legacy=legacy,
                    state=typed,
                    slot=slot,
                    frame=frame_for_generation,
                    section_title=current_title,
                    model_overrides=model_overrides,
                    config=config,
                )
                slot_frame_results[frame_result_key(frame)] = generated_frame
                emit_frame_ready(
                    generation_id=generation_id,
                    section_id=sid,
                    slot=slot,
                    frame=frame,
                    frame_result=generated_frame,
                )
            except asyncio.TimeoutError:
                saw_timeout = True
                message = "Diagram generation timed out for this frame."
                failed_frame = VisualFrameResult(
                    slot_id=slot.slot_id,
                    frame_index=frame.index,
                    label=frame.label,
                    render=slot.preferred_render,
                    status=VisualFrameResultStatus.FAILED,
                    svg_generation_mode=_svg_generation_mode(legacy),
                    model_slot="standard",
                    svg_failure_reason="timeout",
                    error_message=message,
                )
                slot_frame_results[frame_result_key(frame)] = failed_frame
                emit_frame_failed(
                    generation_id=generation_id,
                    section_id=sid,
                    slot=slot,
                    frame=frame,
                    error=message,
                    frame_result=failed_frame,
                )
                errors.append(
                    PipelineError(
                        node="diagram_generator",
                        section_id=sid,
                        message=message,
                        recoverable=True,
                    )
                )
            except Exception as exc:
                message = f"Diagram generation failed for frame {frame.index}: {exc}"
                failed_frame = VisualFrameResult(
                    slot_id=slot.slot_id,
                    frame_index=frame.index,
                    label=frame.label,
                    render=slot.preferred_render,
                    status=VisualFrameResultStatus.FAILED,
                    svg_generation_mode=_svg_generation_mode(legacy),
                    model_slot="standard",
                    sanitized=False,
                    intent_validated=False,
                    svg_failure_reason=_svg_failure_reason(exc),
                    error_message=message,
                )
                slot_frame_results[frame_result_key(frame)] = failed_frame
                emit_frame_failed(
                    generation_id=generation_id,
                    section_id=sid,
                    slot=slot,
                    frame=frame,
                    error=message,
                    frame_result=failed_frame,
                )
                errors.append(
                    PipelineError(
                        node="diagram_generator",
                        section_id=sid,
                        message=message,
                        recoverable=True,
                    )
                )

        section_frame_results[slot.slot_id] = slot_frame_results
        slot_result = build_slot_result(
            slot,
            slot_frame_results,
            error_message=next(
                (
                    result.error_message
                    for result in slot_frame_results.values()
                    if result.status == VisualFrameResultStatus.FAILED
                ),
                None,
            ),
        )
        section_slot_results[slot.slot_id] = slot_result
        updated_section = apply_slot_results_to_section(
            updated_section,
            slot,
            slot_frame_results,
            fallback_diagram=updated_section.diagram,
        )
        emit_slot_state(
            generation_id=generation_id,
            section_id=sid,
            slot=slot,
            ready_frames=slot_result.completed_frames,
            total_frames=slot_result.total_frames,
            error=slot_result.error_message,
            frame_results=slot_frame_results,
        )

    lifecycle = "generated" if all(result.ready for result in section_slot_results.values()) else "partial"
    outcome = "success"
    if errors and not any(result.ready for result in section_slot_results.values()):
        outcome = "timeout" if saw_timeout else "error"
    outcomes = legacy._with_outcome(
        outcomes,
        generation_id=generation_id,
        section_id=sid,
        outcome=outcome,
    )

    output = {
        "generated_sections": {sid: updated_section},
        "media_slot_results": {sid: section_slot_results},
        "media_frame_results": {sid: section_frame_results},
        "media_lifecycle": {sid: lifecycle},
        "diagram_outcomes": outcomes,
        "completed_nodes": ["diagram_generator"],
    }
    if errors:
        output["errors"] = errors
    return output
