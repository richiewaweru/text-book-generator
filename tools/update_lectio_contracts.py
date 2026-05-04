#!/usr/bin/env python3
"""Sync Lectio contracts and generated Python types into backend artifacts."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

META_CONTRACTS = {
    "classification.json",
    "component-examples.json",
    "component-field-map.json",
    "component-registry.json",
    "component-schemas.json",
    "manifest.json",
    "preset-registry.json",
    "print-rules.json",
    "section-content-schema.json",
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


def main() -> int:
    repo_root = _repo_root()
    lectio_dir = _lectio_package_dir(repo_root)
    contracts_source, adapter_source = _required_source_paths(lectio_dir)
    _validate_generated_header(adapter_source)

    contracts_target = repo_root / "backend" / "contracts"
    adapter_target = (
        repo_root / "backend" / "src" / "pipeline" / "types" / "section_content.py"
    )

    copied_contracts = _sync_contracts(contracts_source, contracts_target)
    _sync_generated_adapter(adapter_source, adapter_target)

    template_count = len([p for p in copied_contracts if p.name not in META_CONTRACTS])
    print(f"Synced Lectio contracts from: {contracts_source}")
    print(f"  - total json files: {len(copied_contracts)}")
    print(f"  - template contracts: {template_count}")
    print(f"Synced generated adapter to: {adapter_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
