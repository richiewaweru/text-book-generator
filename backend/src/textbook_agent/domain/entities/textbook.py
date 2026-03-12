from datetime import datetime

from pydantic import BaseModel, Field

from .generation_context import GenerationContext
from .curriculum_plan import CurriculumPlan
from .section_content import SectionContent
from .section_diagram import SectionDiagram
from .section_code import SectionCode


class RawTextbook(BaseModel):
    """Assembled textbook ready for rendering. Output of the Assembler node."""

    subject: str
    profile: GenerationContext
    plan: CurriculumPlan
    sections: list[SectionContent]
    diagrams: list[SectionDiagram] = Field(default_factory=list)
    code_examples: list[SectionCode] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
