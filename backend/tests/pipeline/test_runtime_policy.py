from __future__ import annotations

import pytest

from pipeline.runtime_progress import RuntimeProgressTracker
from pipeline.types.requests import GenerationMode


@pytest.mark.asyncio
async def test_runtime_progress_tracker_tracks_queue_and_completion_state() -> None:
    snapshots = []
    tracker = RuntimeProgressTracker(
        mode=GenerationMode.BALANCED,
        sections_total=3,
        emit_snapshot=snapshots.append,
    )

    await tracker.queue_section("s-01")
    await tracker.start_section("s-01")
    await tracker.queue_node("media", "s-01")
    await tracker.start_node("media", "s-01")
    await tracker.finish_node("media", "s-01")
    await tracker.queue_node("qc", "s-01")
    await tracker.start_node("qc", "s-01")
    await tracker.finish_node("qc", "s-01")
    await tracker.queue_retry("s-01")
    await tracker.start_retry("s-01")
    await tracker.finish_retry("s-01")
    await tracker.mark_section_ready("s-01")
    await tracker.finish_section("s-01")

    final_snapshot = await tracker.snapshot()

    assert final_snapshot.sections_total == 3
    assert final_snapshot.sections_completed == 1
    assert final_snapshot.sections_running == 0
    assert final_snapshot.sections_queued == 0
    assert final_snapshot.media_running == 0
    assert final_snapshot.media_queued == 0
    assert final_snapshot.qc_running == 0
    assert final_snapshot.qc_queued == 0
    assert final_snapshot.retry_running == 0
    assert final_snapshot.retry_queued == 0
    assert any(snapshot.sections_running == 1 for snapshot in snapshots)
    assert any(snapshot.media_running == 1 for snapshot in snapshots)
    assert any(snapshot.qc_running == 1 for snapshot in snapshots)
    assert any(snapshot.retry_running == 1 for snapshot in snapshots)


@pytest.mark.asyncio
async def test_runtime_progress_tracker_skips_duplicate_snapshots() -> None:
    snapshots = []
    tracker = RuntimeProgressTracker(
        mode=GenerationMode.BALANCED,
        sections_total=2,
        emit_snapshot=snapshots.append,
    )

    await tracker.queue_section("s-01")
    await tracker.queue_section("s-01")
    await tracker.start_section("s-01")
    await tracker.start_section("s-01")
    await tracker.mark_section_ready("s-01")
    await tracker.mark_section_ready("s-01")
    await tracker.finish_section("s-01")
    await tracker.finish_section("s-01")

    assert len(snapshots) == 4
    assert [snapshot.sections_queued for snapshot in snapshots] == [1, 0, 0, 0]
    assert [snapshot.sections_running for snapshot in snapshots] == [0, 1, 1, 0]
    assert [snapshot.sections_completed for snapshot in snapshots] == [0, 0, 1, 1]
