from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_synced_lectio_artifacts_exist() -> None:
    root = _repo_root()
    assert (root / "backend" / "contracts" / "section-content-schema.json").exists()
    assert (root / "backend" / "contracts" / "component-registry.json").exists()
    assert (root / "backend" / "contracts" / "component-field-map.json").exists()

    adapter_path = root / "backend" / "src" / "pipeline" / "types" / "section_content.py"
    adapter_text = adapter_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED" in "\n".join(adapter_text.splitlines()[:8])


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
