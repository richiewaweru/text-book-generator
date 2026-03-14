from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    """A single issue found by the Quality Checker."""

    section_id: str | None = None
    issue_type: str
    description: str
    severity: Literal["error", "warning"]
    scope: Literal["section", "document"] = "section"
    check_source: Literal["mechanical", "llm"] = "llm"


class QualityReport(BaseModel):
    """Output of the Quality Checker node."""

    passed: bool
    issues: list[QualityIssue] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.now)
