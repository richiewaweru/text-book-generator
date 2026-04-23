from __future__ import annotations

from pipeline.state import (
    MediaFrameRetryRequest,
    TextbookPipelineState,
    _last_wins,
)

from .test_pipeline_integration import _base_state


def test_last_wins_reducer_accepts_concurrent_none_writes() -> None:
    assert _last_wins("old", None) is None
    assert _last_wins(None, None) is None
    assert _last_wins(None, "new") == "new"


def test_current_media_retry_is_normalized_after_annotation_change() -> None:
    raw = _base_state(current_section_id="s-01").model_dump()
    raw["current_media_retry"] = {
        "section_id": "s-01",
        "slot_id": "diagram",
        "slot_type": "diagram",
        "frame_key": "0",
        "frame_index": 0,
        "executor_node": "diagram_generator",
    }

    parsed = TextbookPipelineState.parse(raw)

    assert isinstance(parsed.current_media_retry, MediaFrameRetryRequest)
    assert parsed.current_media_retry.slot_id == "diagram"


def test_pending_media_retry_for_returns_matching_section_only() -> None:
    state = TextbookPipelineState.parse(
        {
            **_base_state(current_section_id="s-01").model_dump(),
            "current_media_retry": {
                "section_id": "s-01",
                "slot_id": "diagram",
                "slot_type": "diagram",
                "frame_key": "0",
                "frame_index": 0,
                "executor_node": "diagram_generator",
            },
        }
    )

    assert state.pending_media_retry_for("s-01") is not None
    assert state.pending_media_retry_for("s-02") is None
