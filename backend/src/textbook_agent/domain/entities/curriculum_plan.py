from pydantic import BaseModel, Field, model_validator

from textbook_agent.domain.value_objects import SectionDepth


class SectionSpec(BaseModel):
    """Specification for a single section in the curriculum plan."""

    id: str = Field(description="Section identifier e.g. 'section_03'")
    title: str
    learning_objective: str
    prerequisite_ids: list[str] = Field(
        default_factory=list,
        description="Section IDs that must appear before this section",
    )
    needs_diagram: bool = False
    needs_code: bool = False
    is_core: bool = Field(
        default=True,
        description="False = supplementary, can be skipped at survey depth",
    )
    estimated_depth: SectionDepth


class CurriculumPlan(BaseModel):
    """Output of the Curriculum Planner node. Defines the full textbook structure."""

    subject: str
    total_sections: int
    sections: list[SectionSpec]
    reading_order: list[str] = Field(description="Ordered list of section IDs")

    @model_validator(mode="after")
    def validate_consistency(self):
        section_ids = [section.id for section in self.sections]
        if self.total_sections != len(self.sections):
            raise ValueError("total_sections must equal len(sections)")
        if len(self.reading_order) != len(section_ids):
            raise ValueError("reading_order must include every section exactly once")
        if len(set(self.reading_order)) != len(self.reading_order):
            raise ValueError("reading_order must not contain duplicate section IDs")
        if set(self.reading_order) != set(section_ids):
            raise ValueError("reading_order must contain the same section IDs as sections")
        return self
