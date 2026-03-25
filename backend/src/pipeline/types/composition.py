from __future__ import annotations

from pydantic import BaseModel, Field


class DiagramPlan(BaseModel):
    enabled: bool
    reasoning: str
    diagram_type: str | None = None
    focus_area: str | None = None
    key_concepts: list[str] = Field(default_factory=list)
    visual_guidance: str | None = None


class InteractionPlan(BaseModel):
    enabled: bool
    reasoning: str
    interaction_type: str | None = None
    anchor_block: str | None = None


class CompositionPlan(BaseModel):
    diagram: DiagramPlan
    interaction: InteractionPlan
    confidence: str = "high"
    notes: str | None = None
