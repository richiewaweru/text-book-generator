from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import Depth, NotationLanguage


class LearnerProfile(BaseModel):
    """The simplest viable learner profile. Intentionally minimal for Phase 1."""

    subject: str = Field(description="The subject domain e.g. 'calculus', 'DSA', 'linear algebra'")
    age: int = Field(ge=8, le=99, description="Drives vocabulary complexity, example choices, tone")
    context: str = Field(
        description="What the learner knows, what they struggle with, any signals"
    )
    depth: Depth = Field(
        description="Controls section depth and number of worked examples"
    )
    language: NotationLanguage = Field(description="Preferred notation style")
