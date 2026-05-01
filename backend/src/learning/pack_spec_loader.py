from __future__ import annotations

import logging
from pathlib import Path

import yaml

from learning.pack_spec_schema import PackSpec

logger = logging.getLogger(__name__)
_PACK_SPECS_DIR = Path(__file__).parents[2] / "resources" / "pack_specs"
_REGISTRY: dict[str, PackSpec] = {}


def load_all_pack_specs(specs_dir: Path = _PACK_SPECS_DIR) -> dict[str, PackSpec]:
    registry: dict[str, PackSpec] = {}
    paths = sorted(specs_dir.glob("*.yaml"))
    if not paths:
        raise RuntimeError(f"No pack specs found in {specs_dir}")
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                raw = yaml.safe_load(handle)
            spec = PackSpec.model_validate(raw)
        except Exception as exc:
            raise RuntimeError(f"Invalid pack spec {path.name}: {exc}") from exc
        registry[spec.id] = spec
        logger.info("Loaded pack spec: %s v%s", spec.id, spec.version)
    return registry


def get_pack_spec(job_type: str) -> PackSpec:
    if not _REGISTRY:
        _REGISTRY.update(load_all_pack_specs())
    if job_type not in _REGISTRY:
        raise KeyError(f"No pack spec for job type: {job_type}")
    return _REGISTRY[job_type]


def initialize_pack_registry() -> None:
    _REGISTRY.clear()
    _REGISTRY.update(load_all_pack_specs())
    logger.info("Pack spec registry ready: %s", list(_REGISTRY))
