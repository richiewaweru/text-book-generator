from pydantic import BaseModel, Field

from .quality_report import QualityIssue
from .section_code import SectionCode
from .section_content import SectionContent
from .section_diagram import SectionDiagram


class ContentCorrectionContext(BaseModel):
    original_content: SectionContent
    issues: list[QualityIssue] = Field(default_factory=list)


class DiagramCorrectionContext(BaseModel):
    original_diagram: SectionDiagram
    issues: list[QualityIssue] = Field(default_factory=list)


class CodeCorrectionContext(BaseModel):
    original_code: SectionCode
    issues: list[QualityIssue] = Field(default_factory=list)
