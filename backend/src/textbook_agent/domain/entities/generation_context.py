from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)


class GenerationContext(BaseModel):
    """Ephemeral per-generation context assembled from StudentProfile + request.

    This is NOT stored — it is built fresh for each generation run by merging
    the persistent StudentProfile with the per-request fields (subject, context).
    It carries everything the pipeline nodes need to personalise content.

    The ``learner_description`` field is a free-text manual override describing
    the learner's abilities, gaps, and signals. In a future phase this will be
    populated automatically by diagnostic assessments.
    """

    subject: str = Field(description="The subject domain e.g. 'calculus', 'DSA', 'linear algebra'")
    age: int = Field(ge=8, le=99, description="Drives vocabulary complexity, example choices, tone")
    context: str = Field(
        description="What the learner knows about this specific topic, what confuses them"
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
    prior_knowledge: str = Field(
        default="",
        description="Broad prior knowledge the student has across subjects",
    )
    learner_description: str = Field(
        default="",
        description="Free-text description of the learner's abilities, gaps, and signals. "
        "Will be replaced by diagnostic signals in a future phase.",
    )
