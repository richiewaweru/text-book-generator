from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)


class LearnerProfile(BaseModel):
    """Full learner profile hydrated from StudentProfile + per-generation request."""

    subject: str = Field(description="The subject domain e.g. 'calculus', 'DSA', 'linear algebra'")
    age: int = Field(ge=8, le=99, description="Drives vocabulary complexity, example choices, tone")
    context: str = Field(
        description="What the learner knows, what they struggle with, any signals"
    )
    depth: Depth = Field(
        description="Controls section depth and number of worked examples"
    )
    language: NotationLanguage = Field(description="Preferred notation style")
    education_level: EducationLevel = Field(
        default=EducationLevel.HIGH_SCHOOL,
        description="Student's education stage",
    )
    interests: list[str] = Field(
        default_factory=list,
        description="Topics the learner is interested in — used to personalise examples",
    )
    learning_style: LearningStyle = Field(
        default=LearningStyle.READING_WRITING,
        description="Preferred learning modality",
    )
    goals: str = Field(
        default="",
        description="What the learner wants to achieve",
    )
