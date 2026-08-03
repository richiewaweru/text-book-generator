"""Spec-driven lesson skeleton: computed baseline + bounded component/visual edits."""

from v3_blueprint.skeleton.apply import RejectedEdit, apply_edits
from v3_blueprint.skeleton.baseline import build_baseline_skeleton
from v3_blueprint.skeleton.edits import (
    AddComponent,
    RemoveComponent,
    SetVisual,
    SkeletonEdit,
    SwapComponent,
)

__all__ = [
    "AddComponent",
    "RejectedEdit",
    "RemoveComponent",
    "SetVisual",
    "SkeletonEdit",
    "SwapComponent",
    "apply_edits",
    "build_baseline_skeleton",
]
