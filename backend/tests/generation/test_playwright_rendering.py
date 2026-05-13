import logging

from generation.pdf_export.rendering.playwright import _log_print_snapshot


def test_log_print_snapshot_emits_diagnostics_and_failures(caplog) -> None:
    caplog.set_level(logging.INFO, logger="generation.pdf_export.rendering.playwright")

    _log_print_snapshot(
        "gen-123",
        {
            "found": True,
            "renderer": "lectio",
            "fetch_status": "response-200",
            "section_count": "4",
            "template_id": "guided-concept-path",
            "image_count": "3",
            "images_loaded": "2",
            "images_failed": "1",
            "images_timed_out": "false",
            "failed_image_sources": '["https://cdn.example/bad.png"]',
        },
    )

    diagnostic_record = next(
        record for record in caplog.records if record.getMessage() == "PDF render diagnostics"
    )
    assert diagnostic_record.generation_id == "gen-123"
    assert diagnostic_record.renderer == "lectio"
    assert diagnostic_record.fetch_status == "response-200"
    assert diagnostic_record.section_count == "4"
    assert diagnostic_record.image_count == "3"
    assert diagnostic_record.images_loaded == "2"
    assert diagnostic_record.images_failed == "1"
    assert diagnostic_record.images_timed_out == "false"

    failure_record = next(
        record for record in caplog.records if record.getMessage() == "PDF image failures"
    )
    assert failure_record.generation_id == "gen-123"
    assert failure_record.failed_image_sources == '["https://cdn.example/bad.png"]'


def test_log_print_snapshot_skips_missing_root(caplog) -> None:
    caplog.set_level(logging.INFO, logger="generation.pdf_export.rendering.playwright")

    _log_print_snapshot("gen-123", {"found": False})

    assert caplog.records == []
