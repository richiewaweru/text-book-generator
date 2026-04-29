from __future__ import annotations

from pipeline.events import (
    MediaFrameFailedEvent,
    MediaFrameReadyEvent,
    MediaFrameStartedEvent,
    MediaSlotFailedEvent,
    MediaSlotReadyEvent,
)
from pipeline.media.types import VisualFrame, VisualFrameResult, VisualSlot
from pipeline.runtime_diagnostics import publish_runtime_event


def _svg_metadata(frame_result: VisualFrameResult | None) -> dict:
    if frame_result is None:
        return {}
    return {
        "svg_generation_mode": frame_result.svg_generation_mode,
        "model_slot": frame_result.model_slot,
        "diagram_kind": frame_result.diagram_kind,
        "sanitized": frame_result.sanitized,
        "intent_validated": frame_result.intent_validated,
        "svg_failure_reason": frame_result.svg_failure_reason,
    }


def _slot_svg_metadata(frame_results: dict[str, VisualFrameResult] | None) -> dict:
    for frame_result in (frame_results or {}).values():
        if frame_result.svg_generation_mode or frame_result.svg_failure_reason:
            return _svg_metadata(frame_result)
    return {}


def emit_frame_started(
    *,
    generation_id: str,
    section_id: str,
    slot: VisualSlot,
    frame: VisualFrame,
) -> None:
    publish_runtime_event(
        generation_id,
        MediaFrameStartedEvent(
            generation_id=generation_id,
            section_id=section_id,
            slot_id=slot.slot_id,
            slot_type=slot.slot_type.value,
            frame_key=str(frame.index),
            frame_index=frame.index,
            render=slot.preferred_render.value,
            label=frame.label,
        ),
    )


def emit_frame_ready(
    *,
    generation_id: str,
    section_id: str,
    slot: VisualSlot,
    frame: VisualFrame,
    frame_result: VisualFrameResult | None = None,
) -> None:
    publish_runtime_event(
        generation_id,
        MediaFrameReadyEvent(
            generation_id=generation_id,
            section_id=section_id,
            slot_id=slot.slot_id,
            slot_type=slot.slot_type.value,
            frame_key=str(frame.index),
            frame_index=frame.index,
            render=slot.preferred_render.value,
            label=frame.label,
            **_svg_metadata(frame_result),
        ),
    )


def emit_frame_failed(
    *,
    generation_id: str,
    section_id: str,
    slot: VisualSlot,
    frame: VisualFrame,
    error: str,
    frame_result: VisualFrameResult | None = None,
) -> None:
    publish_runtime_event(
        generation_id,
        MediaFrameFailedEvent(
            generation_id=generation_id,
            section_id=section_id,
            slot_id=slot.slot_id,
            slot_type=slot.slot_type.value,
            frame_key=str(frame.index),
            frame_index=frame.index,
            render=slot.preferred_render.value,
            label=frame.label,
            error=error,
            **_svg_metadata(frame_result),
        ),
    )


def emit_slot_state(
    *,
    generation_id: str,
    section_id: str,
    slot: VisualSlot,
    ready_frames: int,
    total_frames: int,
    error: str | None = None,
    frame_results: dict[str, VisualFrameResult] | None = None,
) -> None:
    svg_metadata = _slot_svg_metadata(frame_results)
    if error:
        publish_runtime_event(
            generation_id,
            MediaSlotFailedEvent(
                generation_id=generation_id,
                section_id=section_id,
                slot_id=slot.slot_id,
                slot_type=slot.slot_type.value,
                ready_frames=ready_frames,
                total_frames=total_frames,
                error=error,
                **svg_metadata,
            ),
        )
        return

    publish_runtime_event(
        generation_id,
        MediaSlotReadyEvent(
            generation_id=generation_id,
            section_id=section_id,
            slot_id=slot.slot_id,
            slot_type=slot.slot_type.value,
            ready_frames=ready_frames,
            total_frames=total_frames,
            **svg_metadata,
        ),
    )
