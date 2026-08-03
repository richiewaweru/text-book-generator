"""Typed skeleton edits — component and visual moves only (Arm C narrowed)."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class SwapComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["swap_component"] = "swap_component"
    section_id: str
    from_slug: str
    to_slug: str
    reason: str


class AddComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["add_component"] = "add_component"
    section_id: str
    slug: str
    reason: str


class RemoveComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["remove_component"] = "remove_component"
    section_id: str
    slug: str
    reason: str


class SetVisual(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["set_visual"] = "set_visual"
    section_id: str
    visual_required: bool
    reason: str


SkeletonEdit = Annotated[
    Union[SwapComponent, AddComponent, RemoveComponent, SetVisual],
    Field(discriminator="kind"),
]
