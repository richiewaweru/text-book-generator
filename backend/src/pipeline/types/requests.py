"""
pipeline.types.requests

Input types for the generation pipeline.
"""

from __future__ import annotations

from enum import Enum

from pydantic import AliasChoices, BaseModel, Field

from pipeline.types.section_content import SectionContent


class GenerationMode(str, Enum):
    DRAFT = "draft"
    BALANCED = "balanced"
    STRICT = "strict"


class SeedDocument(BaseModel):
    sections: list[SectionContent] = Field(default_factory=list)
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
    seed_document: SeedDocument | None = None

    @property
    def topic(self) -> str:
        return self.context

    def max_rerenders(self) -> int:
        if self.mode == GenerationMode.DRAFT:
            return 0
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
    bridges_from: str | None = None
    bridges_to: str | None = None
    needs_diagram: bool = False
    needs_worked_example: bool = False
