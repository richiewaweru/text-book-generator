from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_synced_lectio_artifacts_exist() -> None:
    root = _repo_root()
    assert (root / "backend" / "contracts" / "lectio-content-contract.json").exists(), (
        "lectio-content-contract.json is missing. "
        "Run: uv run python tools/update_lectio_contracts.py"
    )
    assert (root / "backend" / "contracts" / "section-content-schema.json").exists(), (
        "section-content-schema.json is missing. "
        "Run: uv run python tools/update_lectio_contracts.py"
    )

    adapter_path = root / "backend" / "src" / "pipeline" / "types" / "section_content.py"
    assert adapter_path.exists(), "section_content.py Pydantic adapter is missing."
    adapter_text = adapter_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED" in "\n".join(adapter_text.splitlines()[:8]), (
        "section_content.py does not have an AUTO-GENERATED header. "
        "This file must be generated from section-content-schema.json, not hand-edited."
    )


def test_lectio_content_contract_has_required_structure() -> None:
    root = _repo_root()
    contract_path = root / "backend" / "contracts" / "lectio-content-contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    assert "component_cards" in contract, "missing component_cards"
    assert "planner_index" in contract, "missing planner_index"
    assert "templates" in contract, "missing templates"
    assert "formatting_policy" in contract, "missing formatting_policy"

    cards = contract["component_cards"]
    assert "explanation-block" in cards, "explanation-block missing from component_cards"
    card = cards["explanation-block"]
    assert card.get("section_field") == "explanation", (
        f"explanation-block section_field wrong: {card.get('section_field')}"
    )
    assert "field_contracts" in card, "explanation-block missing field_contracts"
    assert "body" in card["field_contracts"], "explanation-block field_contracts missing 'body'"

    phase_map = contract["planner_index"].get("phase_map", {})
    assert "1" in phase_map, "phase_map missing phase 1"
    assert "name" in phase_map["1"], "phase_map phase 1 missing name field"
    assert phase_map["1"]["name"] == "Orient", (
        f"Expected phase 1 name 'Orient', got '{phase_map['1'].get('name')}'"
    )
    assert "components" in phase_map["1"], "phase_map phase 1 missing components list"

    templates = contract.get("templates", {})
    assert "guided-concept-path" in templates, "guided-concept-path missing from templates"
    template = templates["guided-concept-path"]
    assert "available_components" in template, "guided-concept-path missing available_components"

    assert "print_surface" in contract, "missing print_surface"
    ps = contract["print_surface"]
    assert isinstance(ps, dict), "print_surface must be an object"
    assert ps.get("usable_height_px") == 970, f"unexpected usable_height_px: {ps.get('usable_height_px')}"

    ds = cards.get("diagram-series")
    assert ds is not None, "diagram-series missing from component_cards"
    assert ds.get("print", {}).get("breakBehavior") == "itemized", (
        f"diagram-series print.breakBehavior wrong: {ds.get('print')}"
    )


def test_get_lectio_print_surface_helper() -> None:
    from pipeline.contracts import get_lectio_print_surface

    surf = get_lectio_print_surface()
    assert isinstance(surf, dict)
    assert surf.get("usable_height_px") == 970


def test_sync_rejects_non_generated_adapter(tmp_path: Path) -> None:
    script_path = _repo_root() / "tools" / "update_lectio_contracts.py"
    spec = importlib.util.spec_from_file_location("update_lectio_contracts", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    bad_file = tmp_path / "section_content.py"
    bad_file.write_text("class NotGenerated: pass\n", encoding="utf-8")

    with pytest.raises(ValueError):
        module._validate_generated_header(bad_file)
