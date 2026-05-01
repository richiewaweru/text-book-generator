from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PackResourceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    resource_type: str
    intended_outcome: str
    label: str
    purpose: str
    depth: str
    required: bool
    order: int


class PackPlanGuidance(BaseModel):
    model_config = ConfigDict(extra="ignore")

    objective_focus: str | None = None
    example_guidance: str | None = None
    misconception_focus: str | None = None
    vocabulary_priority: str | None = None


class PackSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    version: str
    intent: str
    plan_guidance: PackPlanGuidance = Field(default_factory=PackPlanGuidance)
    resources: list[PackResourceEntry]
    default_supports: list[str] = Field(default_factory=list)
    validation: list[str] = Field(default_factory=list)

