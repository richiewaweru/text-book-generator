from __future__ import annotations

import logging
from pathlib import Path

import yaml

from generation.v3_lenses.schema import LensSchema

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[3]
_LENSES_DIR = _BACKEND_ROOT / "resources" / "lenses"
_REGISTRY: dict[str, LensSchema] = {}


def load_all_lenses(lenses_dir: Path | None = None) -> dict[str, LensSchema]:
    base = lenses_dir or _LENSES_DIR
    registry: dict[str, LensSchema] = {}
    for path in sorted(base.rglob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            continue
        lens = LensSchema.model_validate(raw)
        registry[lens.id] = lens
        logger.info("Loaded lens: %s (%s)", lens.id, lens.category)
    if not registry:
        raise RuntimeError(f"No lenses found in {base}")
    return registry


def get_all_lenses() -> list[LensSchema]:
    if not _REGISTRY:
        _REGISTRY.update(load_all_lenses())
    return list(_REGISTRY.values())


def get_lens(lens_id: str) -> LensSchema:
    if not _REGISTRY:
        _REGISTRY.update(load_all_lenses())
    return _REGISTRY[lens_id]


def format_lenses_for_prompt() -> str:
    lines = ["Pedagogical lenses — apply those that fit the teacher's signals:"]
    for lens in sorted(get_all_lenses(), key=lambda item: item.id):
        lines.append(f"\n  {lens.id} ({lens.label}) — {lens.applies_when.strip()}")
        lines.append("  Principles:")
        for principle in lens.reasoning_principles[:3]:
            lines.append(f"    - {principle}")
        if lens.avoid:
            lines.append(f"  Avoid: {', '.join(lens.avoid[:3])}")
    return "\n".join(lines)
