#!/usr/bin/env python3
"""Sync Lectio contracts and generated Python types into backend artifacts."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

META_CONTRACTS = {
    "component-field-map.json",
    "component-registry.json",
    "preset-registry.json",
    "section-content-schema.json",
}

_INLINE_DIAGRAM_FIELDS: dict[str, str] = {
    "PracticeProblem": "context: Optional[str] = None",
    "WorkedExampleContent": "alternatives: Optional[list[str]] = None",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _lectio_package_dir(repo_root: Path) -> Path:
    override = os.environ.get("LECTIO_PACKAGE_DIR")
    if override:
        candidate = Path(override)
    else:
        candidate = repo_root / "frontend" / "node_modules" / "lectio"

    if not candidate.exists():
        raise FileNotFoundError(
            f"Lectio package not found at '{candidate}'. "
            "Install frontend deps first or set LECTIO_PACKAGE_DIR."
        )
    return candidate


def _required_source_paths(lectio_dir: Path) -> tuple[Path, Path]:
    contracts_dir = lectio_dir / "contracts"
    generated_adapter = lectio_dir / "generated" / "python" / "section_content.py"

    if not contracts_dir.exists():
        raise FileNotFoundError(f"Missing Lectio contracts directory: '{contracts_dir}'")
    if not generated_adapter.exists():
        raise FileNotFoundError(f"Missing generated adapter: '{generated_adapter}'")

    return contracts_dir, generated_adapter


def _lectio_ts_types_path(lectio_dir: Path) -> Path:
    candidate = lectio_dir / "dist" / "schema" / "types.d.ts"
    if not candidate.exists():
        raise FileNotFoundError(f"Missing Lectio TypeScript declarations: '{candidate}'")
    return candidate


def _validate_generated_header(adapter_path: Path) -> None:
    header = adapter_path.read_text(encoding="utf-8").splitlines()[:8]
    if not any("AUTO-GENERATED" in line for line in header):
        raise ValueError(
            f"Generated adapter '{adapter_path}' is missing an AUTO-GENERATED header."
        )


def _sync_contracts(source_dir: Path, target_dir: Path) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)

    source_json_files = sorted(source_dir.glob("*.json"))
    if not source_json_files:
        raise FileNotFoundError(f"No contract json files found in '{source_dir}'")

    source_names = {path.name for path in source_json_files}

    for stale in target_dir.glob("*.json"):
        if stale.name not in source_names:
            stale.unlink()

    copied: list[Path] = []
    for source in source_json_files:
        target = target_dir / source.name
        shutil.copy2(source, target)
        copied.append(target)

    missing_meta = [
        name for name in sorted(META_CONTRACTS) if not (target_dir / name).exists()
    ]
    if missing_meta:
        raise FileNotFoundError(
            "Missing required Lectio contract artifacts after sync: "
            + ", ".join(missing_meta)
        )

    return copied


def _sync_generated_adapter(source_adapter: Path, target_adapter: Path) -> None:
    target_adapter.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_adapter, target_adapter)

    # Re-validate target file after copy to prevent accidental hand-authored replacements.
    _validate_generated_header(target_adapter)


def _supports_inline_diagram_fields(lectio_types_path: Path) -> bool:
    declarations = lectio_types_path.read_text(encoding="utf-8")
    required_patterns = [
        r"export interface PracticeProblem \{\s+diagram\?: DiagramContent;",
        r"export interface WorkedExampleContent \{\s+diagram\?: DiagramContent;",
    ]
    return all(re.search(pattern, declarations, re.MULTILINE) for pattern in required_patterns)


def _augment_contract_schema_for_inline_diagrams(schema_path: Path) -> None:
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    definitions = payload.setdefault("definitions", {})
    for definition_name in _INLINE_DIAGRAM_FIELDS:
        definition = definitions.get(definition_name)
        if not isinstance(definition, dict):
            continue
        properties = definition.setdefault("properties", {})
        properties.setdefault("diagram", {"$ref": "#/definitions/DiagramContent"})
    schema_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _augment_generated_adapter_for_inline_diagrams(adapter_path: Path) -> None:
    text = adapter_path.read_text(encoding="utf-8")
    for class_name, anchor in _INLINE_DIAGRAM_FIELDS.items():
        marker = f"class {class_name}(BaseModel):"
        if marker not in text:
            continue
        class_start = text.index(marker)
        next_class = text.find("\nclass ", class_start + len(marker))
        class_end = len(text) if next_class == -1 else next_class
        class_block = text[class_start:class_end]
        if "diagram: Optional[DiagramContent] = None" in class_block:
            continue
        anchor_line = f"    {anchor}"
        if anchor_line not in class_block:
            continue
        updated_block = class_block.replace(
            anchor_line,
            anchor_line + "\n    diagram: Optional[DiagramContent] = None",
            1,
        )
        text = text[:class_start] + updated_block + text[class_end:]
    adapter_path.write_text(text, encoding="utf-8")


def main() -> int:
    repo_root = _repo_root()
    lectio_dir = _lectio_package_dir(repo_root)
    contracts_source, adapter_source = _required_source_paths(lectio_dir)
    lectio_types_path = _lectio_ts_types_path(lectio_dir)
    _validate_generated_header(adapter_source)

    contracts_target = repo_root / "backend" / "contracts"
    adapter_target = (
        repo_root / "backend" / "src" / "pipeline" / "types" / "section_content.py"
    )

    copied_contracts = _sync_contracts(contracts_source, contracts_target)
    _sync_generated_adapter(adapter_source, adapter_target)
    if _supports_inline_diagram_fields(lectio_types_path):
        _augment_contract_schema_for_inline_diagrams(contracts_target / "section-content-schema.json")
        _augment_generated_adapter_for_inline_diagrams(adapter_target)

    template_count = len([p for p in copied_contracts if p.name not in META_CONTRACTS])
    print(f"Synced Lectio contracts from: {contracts_source}")
    print(f"  - total json files: {len(copied_contracts)}")
    print(f"  - template contracts: {template_count}")
    print(f"Synced generated adapter to: {adapter_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
