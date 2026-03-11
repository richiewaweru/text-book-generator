from enum import Enum


class LearningStyle(str, Enum):
    """Preferred mode of learning."""

    VISUAL = "visual"
    READING_WRITING = "reading_writing"
    KINESTHETIC = "kinesthetic"
    AUDITORY = "auditory"
