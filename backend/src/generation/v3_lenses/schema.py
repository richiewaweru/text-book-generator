from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LensSchema(BaseModel):
    id: str
    label: str
    category: Literal["lesson", "support"]
    applies_when: str
    reasoning_principles: list[str]
    blueprint_effects: dict[str, str]
    principles: dict[str, str]
    avoid: list[str] = []
    conflicts_with: list[str] = []
