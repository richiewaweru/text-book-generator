from __future__ import annotations

from pydantic import BaseModel, Field


class SectionPlanEnrichment(BaseModel):
    section_id: str
    terms_to_define: list[str] = Field(default_factory=list)
    terms_assumed: list[str] = Field(default_factory=list)
    practice_target: str | None = None
    bridges_from: str | None = None
    bridges_to: str | None = None


class CurriculumEnrichmentOutput(BaseModel):
    sections: list[SectionPlanEnrichment] = Field(default_factory=list)
