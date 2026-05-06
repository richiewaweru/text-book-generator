from __future__ import annotations

import json
from pathlib import Path

import pytest

from v3_blueprint.models import ProductionBlueprint
from v3_execution.compile_orders import compile_execution_bundle
from v3_execution.executors.section_writer import execute_section


def _load_example(filename: str) -> ProductionBlueprint:
    raw = Path(__file__).resolve().parents[2] / "src" / "v3_blueprint" / "examples" / filename
    return ProductionBlueprint.model_validate(json.loads(raw.read_text(encoding="utf-8")))


@pytest.mark.asyncio
async def test_section_writer_emits_failed_event_before_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bp = _load_example("amara_compound_area.json")
    bundle = compile_execution_bundle(
        bp,
        generation_id="gen-1",
        blueprint_id="bp-1",
        template_id="guided-concept-path",
    )
    order = bundle.section_orders[0]

    async def stub_json_agent(**_kwargs):
        # Missing fields force execute_section to fail validation/coverage.
        return {}

    monkeypatch.setattr(
        "v3_execution.executors.section_writer.run_json_agent",
        stub_json_agent,
    )

    captured: list[tuple[str, dict[str, object]]] = []

    async def emit(event_type: str, payload: dict[str, object]) -> None:
        captured.append((event_type, payload))

    with pytest.raises(RuntimeError):
        await execute_section(
            order,
            emit,
            trace_id="trace-1",
            generation_id="gen-1",
            model_overrides=None,
        )

    event_types = [event for event, _payload in captured]
    assert "section_writing_started" in event_types
    assert "section_writer_failed" in event_types
    failed_payload = next(payload for event, payload in captured if event == "section_writer_failed")
    assert failed_payload["generation_id"] == "gen-1"
    assert failed_payload["section_id"] == order.section.id
    assert isinstance(failed_payload["errors"], list)
    assert isinstance(failed_payload["warnings"], list)

