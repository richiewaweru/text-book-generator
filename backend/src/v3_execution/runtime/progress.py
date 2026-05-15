from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from v3_blueprint.models import ProductionBlueprint

from v3_execution.runtime import events

EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


def section_titles_from_blueprint(blueprint: ProductionBlueprint) -> dict[str, str]:
    return {section.section_id: section.title for section in blueprint.sections}


def titled_label(prefix: str, title: str | None, *, fallback: str) -> str:
    cleaned = (title or "").strip()
    if cleaned:
        return f"{prefix}: {cleaned}"
    return fallback


async def emit_progress(
    emit_event: EmitFn,
    *,
    generation_id: str,
    stage: str,
    label: str,
    section_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "generation_id": generation_id,
        "stage": stage,
        "label": label,
    }
    if section_id:
        payload["section_id"] = section_id
    await emit_event(events.PROGRESS_UPDATE, payload)


__all__ = [
    "EmitFn",
    "emit_progress",
    "section_titles_from_blueprint",
    "titled_label",
]
