from __future__ import annotations

import logging
from typing import Literal

from fastapi import HTTPException

logger = logging.getLogger(__name__)

SupplementType = Literal["exit_ticket", "quiz", "worksheet"]

DEFAULT_PARENT_RESOURCE_TYPE = "lesson"

ALLOWED_SUPPLEMENTS: dict[str, set[str]] = {
    "lesson": {"exit_ticket", "quiz", "worksheet"},
    "mini_booklet": {"exit_ticket", "quiz", "worksheet"},
    "worksheet": {"exit_ticket", "quiz"},
    "quick_explainer": {"exit_ticket", "worksheet"},
    "practice_set": {"exit_ticket", "quiz"},
    "quiz": set(),
    "exit_ticket": set(),
}

SUPPLEMENT_OPTION_METADATA: dict[str, dict[str, str]] = {
    "exit_ticket": {
        "label": "Exit Ticket",
        "description": "3 quick questions to check understanding at the end of the lesson.",
        "best_for": "End-of-lesson check",
        "estimated_length": "5 minutes",
    },
    "quiz": {
        "label": "Quiz",
        "description": "A formal printable assessment with an answer key at the end of the PDF.",
        "best_for": "Graded or recorded assessment",
        "estimated_length": "10-20 minutes",
    },
    "worksheet": {
        "label": "Practice Worksheet",
        "description": "Guided-to-independent practice based on the completed lesson.",
        "best_for": "Classwork or homework",
        "estimated_length": "20-30 minutes",
    },
}


def _normalize_resource_type(resource_type: str | None) -> str:
    if not resource_type or not str(resource_type).strip():
        return DEFAULT_PARENT_RESOURCE_TYPE
    return str(resource_type).lower().strip().replace(" ", "_")


def allowed_supplements_for(
    parent_resource_type: str,
    available_spec_ids: set[str],
) -> list[str]:
    """Return allowed supplement resource types that also have YAML specs."""
    parent = _normalize_resource_type(parent_resource_type)
    allowed = ALLOWED_SUPPLEMENTS.get(parent)
    if allowed is None:
        logger.warning(
            "Unknown parent resource type %r; falling back to %s",
            parent_resource_type,
            DEFAULT_PARENT_RESOURCE_TYPE,
        )
        allowed = ALLOWED_SUPPLEMENTS[DEFAULT_PARENT_RESOURCE_TYPE]
    return sorted(rt for rt in allowed if rt in available_spec_ids)


def is_supplement_allowed(
    *,
    parent_resource_type: str,
    target_resource_type: str,
    available_spec_ids: set[str],
) -> bool:
    """Return true only if matrix allows it and spec exists."""
    target = _normalize_resource_type(target_resource_type)
    if target not in available_spec_ids:
        return False
    return target in allowed_supplements_for(parent_resource_type, available_spec_ids)


def assert_supplement_allowed(
    *,
    parent_resource_type: str,
    target_resource_type: str,
    available_spec_ids: set[str],
) -> None:
    """Raise HTTP 422 if supplement type is invalid or not allowed."""
    target = _normalize_resource_type(target_resource_type)
    if target not in available_spec_ids:
        raise HTTPException(
            status_code=422,
            detail=f"Resource type '{target_resource_type}' is not supported.",
        )
    if not is_supplement_allowed(
        parent_resource_type=parent_resource_type,
        target_resource_type=target,
        available_spec_ids=available_spec_ids,
    ):
        parent = _normalize_resource_type(parent_resource_type)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Companion resource '{target}' is not allowed for parent type '{parent}'."
            ),
        )


def parent_resource_type_from_artifact(artifact: dict) -> str:
    derived = artifact.get("derived")
    if isinstance(derived, dict):
        rt = derived.get("resource_type")
        if isinstance(rt, str) and rt.strip():
            return _normalize_resource_type(rt)
    blueprint = artifact.get("blueprint")
    if isinstance(blueprint, dict):
        lesson = blueprint.get("lesson")
        if isinstance(lesson, dict):
            rt = lesson.get("resource_type")
            if isinstance(rt, str) and rt.strip():
                return _normalize_resource_type(rt)
    return DEFAULT_PARENT_RESOURCE_TYPE


__all__ = [
    "ALLOWED_SUPPLEMENTS",
    "DEFAULT_PARENT_RESOURCE_TYPE",
    "SUPPLEMENT_OPTION_METADATA",
    "SupplementType",
    "allowed_supplements_for",
    "assert_supplement_allowed",
    "is_supplement_allowed",
    "parent_resource_type_from_artifact",
]
