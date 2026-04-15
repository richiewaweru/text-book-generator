from generation.service import _progress_updates_for_event


def test_section_attempt_started_initial_maps_to_generating_section() -> None:
    updates = _progress_updates_for_event(
        {
            "type": "section_attempt_started",
            "generation_id": "gen-1",
            "section_id": "s-01",
            "attempt": 1,
            "trigger": "initial",
        }
    )

    assert updates == [
        {
            "type": "progress_update",
            "generation_id": "gen-1",
            "stage": "generating_section",
            "section_id": "s-01",
            "label": "Generating section",
        }
    ]


def test_section_attempt_started_rerender_maps_to_repairing() -> None:
    updates = _progress_updates_for_event(
        {
            "type": "section_attempt_started",
            "generation_id": "gen-1",
            "section_id": "s-01",
            "attempt": 2,
            "trigger": "rerender",
        }
    )

    assert updates == [
        {
            "type": "progress_update",
            "generation_id": "gen-1",
            "stage": "repairing",
            "section_id": "s-01",
            "label": "Repairing section",
        }
    ]


def test_section_retry_queued_stays_repairing() -> None:
    updates = _progress_updates_for_event(
        {
            "type": "section_retry_queued",
            "generation_id": "gen-1",
            "section_id": "s-01",
        }
    )

    assert updates == [
        {
            "type": "progress_update",
            "generation_id": "gen-1",
            "stage": "repairing",
            "section_id": "s-01",
            "label": "Repairing section",
        }
    ]


def test_section_started_no_longer_synthesizes_progress_update() -> None:
    updates = _progress_updates_for_event(
        {
            "type": "section_started",
            "generation_id": "gen-1",
            "section_id": "s-01",
            "title": "First section",
            "position": 1,
        }
    )

    assert updates == []
