"""
pipeline.contracts

The pipeline's interface to the Lectio library.

The pipeline asks questions. This module reads from the exported
contract JSON files and answers them. No pipeline node imports
from Lectio's source or knows the JSON structure directly.

Contract files are produced by:
    cd lectio && npm run export-contracts -- --out <path>/backend/contracts

The contracts directory is resolved in this order:
    1. LECTIO_CONTRACTS_DIR environment variable
    2. backend/contracts/ relative to this file's package root
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

from pipeline.types.template_contract import TemplateContractSummary, TemplatePresetSummary


# ── Directory resolution ─────────────────────────────────────────────────────

def _contracts_dir() -> Path:
    from_env = os.environ.get("LECTIO_CONTRACTS_DIR")
    if from_env:
        path = Path(from_env)
        if not path.exists():
            raise FileNotFoundError(
                f"LECTIO_CONTRACTS_DIR is set to '{from_env}' "
                f"but the directory does not exist. "
                f"Run: cd lectio && npm run export-contracts -- --out {from_env}"
            )
        return path

    # Walk up from src/pipeline/contracts.py → src/pipeline → src → backend/contracts
    default = Path(__file__).resolve().parent.parent.parent / "contracts"
    if not default.exists():
        raise FileNotFoundError(
            f"Contracts directory not found at '{default}'. "
            f"Run: cd lectio && npm run export-contracts -- --out {default}"
        )
    return default


# ── Raw loaders (cached) ─────────────────────────────────────────────────────

_META_FILES = {"component-field-map", "component-registry", "preset-registry"}


def diag(tag: str, **fields) -> None:
    sys.stderr.write(f"DIAG::{tag}::{json.dumps(fields, default=str)}\n")
    sys.stderr.flush()


@lru_cache(maxsize=None)
def _load_contract_raw(template_id: str) -> dict:
    path = _contracts_dir() / f"{template_id}.json"
    if not path.exists():
        available = [
            p.stem for p in _contracts_dir().glob("*.json")
            if p.stem not in _META_FILES
        ]
        raise ValueError(
            f"No contract found for template '{template_id}'. "
            f"Available templates: {sorted(available)}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load_field_map() -> dict[str, str]:
    path = _contracts_dir() / "component-field-map.json"
    if not path.exists():
        raise FileNotFoundError(
            "component-field-map.json not found. "
            "Run: cd lectio && npm run export-contracts"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load_component_registry() -> dict[str, dict]:
    path = _contracts_dir() / "component-registry.json"
    if not path.exists():
        raise FileNotFoundError("component-registry.json not found.")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _load_preset_registry() -> dict[str, dict]:
    path = _contracts_dir() / "preset-registry.json"
    if not path.exists():
        raise FileNotFoundError(
            "preset-registry.json not found. "
            "Run: cd lectio && npm run export-contracts"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _required_components(contract: dict) -> list[str]:
    template_id = contract.get("id")
    required = contract.get("required_components")
    if isinstance(required, list):
        diag(
            "CONTRACT_RESOLVED_REQUIREMENTS",
            template_id=template_id,
            required_components=required,
            always_present=contract.get("always_present"),
            resolved_required_components=required,
            source="required_components",
        )
        return required

    always_present = contract.get("always_present")
    if isinstance(always_present, list):
        diag(
            "CONTRACT_RESOLVED_REQUIREMENTS",
            template_id=template_id,
            required_components=contract.get("required_components"),
            always_present=always_present,
            resolved_required_components=always_present,
            source="always_present",
        )
        return always_present

    diag(
        "CONTRACT_RESOLVED_REQUIREMENTS",
        template_id=template_id,
        required_components=contract.get("required_components"),
        always_present=contract.get("always_present"),
        resolved_required_components=[],
        source="none",
    )
    return []


def _optional_components(contract: dict) -> list[str]:
    optional = contract.get("optional_components")
    if isinstance(optional, list):
        return optional

    available = contract.get("available_components")
    if not isinstance(available, list):
        return []

    required = set(_required_components(contract))
    return [component_id for component_id in available if component_id not in required]


# ── Public API ───────────────────────────────────────────────────────────────

def get_contract(template_id: str) -> TemplateContractSummary:
    raw = _load_contract_raw(template_id)
    return TemplateContractSummary.model_validate(raw)


def get_preset(preset_id: str) -> TemplatePresetSummary:
    registry = _load_preset_registry()
    if preset_id not in registry:
        raise ValueError(
            f"Unknown preset '{preset_id}'. "
            f"Available: {sorted(registry.keys())}"
        )
    return TemplatePresetSummary.model_validate(registry[preset_id])


def list_template_ids() -> list[str]:
    return sorted(
        p.stem for p in _contracts_dir().glob("*.json")
        if p.stem not in _META_FILES
    )


def get_required_fields(template_id: str) -> list[str]:
    contract = _load_contract_raw(template_id)
    field_map = _load_field_map()
    return [
        field_map[cid]
        for cid in _required_components(contract)
        if cid in field_map
    ]


def get_optional_fields(template_id: str) -> list[str]:
    contract = _load_contract_raw(template_id)
    field_map = _load_field_map()
    return [
        field_map[cid]
        for cid in _optional_components(contract)
        if cid in field_map
    ]


def get_generation_guidance(template_id: str) -> dict:
    return _load_contract_raw(template_id).get("generation_guidance", {})


def get_lesson_flow(template_id: str) -> list[str]:
    return _load_contract_raw(template_id).get("lesson_flow", [])


def validate_section_for_template(
    section: dict,
    template_id: str,
    *,
    mode: str = "final",
    allow_missing_fields: set[str] | None = None,
    additional_required_fields: set[str] | None = None,
) -> tuple[bool, list[str]]:
    violations = []
    field_map = _load_field_map()
    contract = _load_contract_raw(template_id)
    resolved_required_components = _required_components(contract)
    allowed_missing_fields = allow_missing_fields or set()
    extra_required_fields = additional_required_fields or set()
    diag(
        "CONTRACT_VALIDATION_START",
        template_id=template_id,
        mode=mode,
        resolved_required_components=resolved_required_components,
        section_keys=sorted(section.keys()),
        allow_missing_fields=sorted(allowed_missing_fields),
        additional_required_fields=sorted(extra_required_fields),
    )

    for component_id in resolved_required_components:
        field = field_map.get(component_id)
        content_present = bool(section.get(field)) if field is not None else False
        diag(
            "CONTRACT_REQUIRED_CHECK",
            template_id=template_id,
            component_id=component_id,
            field=field,
            content_present=content_present,
        )
        if field is None:
            continue
        if mode == "partial" and field in allowed_missing_fields:
            continue
        if not section.get(field):
            violations.append(
                f"Required component '{component_id}' has no content "
                f"(missing field: '{field}')"
            )

    for field in sorted(extra_required_fields):
        if mode == "partial" and field in allowed_missing_fields:
            continue
        if not section.get(field):
            violations.append(
                f"Required field '{field}' has no content for template '{template_id}'"
            )

    if section.get("template_id") != template_id:
        violations.append(
            f"Section template_id '{section.get('template_id')}' "
            f"does not match expected '{template_id}'"
        )

    diag(
        "CONTRACT_VALIDATION_RESULT",
        template_id=template_id,
        violations=violations,
    )
    return len(violations) == 0, violations


def get_capacity_limits(component_id: str) -> dict:
    registry = _load_component_registry()
    if component_id not in registry:
        return {}
    return registry[component_id].get("capacity", {})


def get_component_registry_entry(component_id: str) -> dict | None:
    """Return raw registry metadata for a component, or None if unknown."""
    registry = _load_component_registry()
    return registry.get(component_id)


def get_section_field_for_component(component_id: str) -> str | None:
    """Map component id to SectionContent field name (from exported field map)."""
    field_map = _load_field_map()
    return field_map.get(component_id)


def get_allowed_presets(template_id: str) -> list[str]:
    return _load_contract_raw(template_id).get("allowed_presets", [])


def validate_preset_for_template(template_id: str, preset_id: str) -> bool:
    return preset_id in get_allowed_presets(template_id)


def clear_cache() -> None:
    _load_contract_raw.cache_clear()
    _load_field_map.cache_clear()
    _load_component_registry.cache_clear()
    _load_preset_registry.cache_clear()
