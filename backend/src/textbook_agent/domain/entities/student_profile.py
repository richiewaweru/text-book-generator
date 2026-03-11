from datetime import datetime

from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)


class StudentProfile(BaseModel):
    """Persistent student profile — captures who the student is across sessions."""

    id: str
    user_id: str
    age: int = Field(ge=8, le=99)
    education_level: EducationLevel
    interests: list[str] = Field(default_factory=list)
    learning_style: LearningStyle
    preferred_notation: NotationLanguage = NotationLanguage.PLAIN
    prior_knowledge: str = ""
    goals: str = ""
    preferred_depth: Depth = Depth.STANDARD
    created_at: datetime
    updated_at: datetime
