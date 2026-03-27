"""
pipeline.types.requests

Input types for the generation pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, Field

from pipeline.types.section_content import SectionContent


class GenerationMode(str, Enum):
    DRAFT = "draft"
    BALANCED = "balanced"
    STRICT = "strict"


class SeedDocument(BaseModel):
    sections: list[SectionContent] = Field(default_factory=list)
    section_plans: list["SectionPlan"] = Field(default_factory=list)
    qc_reports: list[dict] = Field(default_factory=list)
    note: str = ""


class PipelineRequest(BaseModel):
    subject: str
    context: str = Field(validation_alias=AliasChoices("context", "topic"))
    grade_band: str
    template_id: str
    preset_id: str
    learner_fit: str = "general"
    section_count: int = 4
    mode: GenerationMode = GenerationMode.BALANCED
    generation_id: str | None = None
    source_generation_id: str | None = None
    section_plans: list["SectionPlan"] | None = None
    seed_document: SeedDocument | None = None
    target_section_ids: list[str] | None = None
    target_component: str | None = None

    @property
    def topic(self) -> str:
        return self.context

    def max_rerenders(self) -> int:
        if self.mode == GenerationMode.DRAFT:
            return 1
        if self.mode == GenerationMode.STRICT:
            return 3
        return 2

    def interactions_enabled(self) -> bool:
        return self.mode != GenerationMode.DRAFT


class SectionPlan(BaseModel):
    """One entry in the curriculum outline produced by curriculum_planner."""

    section_id: str
    title: str
    position: int
    focus: str
    role: Literal["intro", "develop", "practice", "synthesis"] = "develop"
    bridges_from: str | None = None
    bridges_to: str | None = None
    needs_diagram: bool = False
    needs_worked_example: bool = False
    required_components: list[str] = Field(default_factory=list)
    optional_components: list[str] = Field(default_factory=list)
    interaction_policy: Literal["required", "allowed", "disabled"] = "allowed"
    diagram_policy: Literal["required", "allowed", "disabled"] = "allowed"
    enrichment_enabled: bool = True
    continuity_notes: str | None = None
