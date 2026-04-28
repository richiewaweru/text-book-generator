from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TeacherBriefOutcome = Literal[
    "understand",
    "practice",
    "review",
    "assess",
    "compare",
    "vocabulary",
]
TeacherBriefResourceType = Literal[
    "worksheet",
    "mini_booklet",
    "exit_ticket",
    "quick_explainer",
    "practice_set",
    "quiz",
]
TeacherBriefSupport = Literal[
    "visuals",
    "vocabulary_support",
    "worked_examples",
    "step_by_step",
    "discussion_questions",
    "simpler_reading",
    "challenge_questions",
]
TeacherBriefDepth = Literal["quick", "standard", "deep"]
TeacherGradeLevel = Literal[
    "pre_k",
    "kindergarten",
    "grade_1",
    "grade_2",
    "grade_3",
    "grade_4",
    "grade_5",
    "grade_6",
    "grade_7",
    "grade_8",
    "grade_9",
    "grade_10",
    "grade_11",
    "grade_12",
    "college",
    "adult",
    "mixed",
]
TeacherGradeBand = Literal[
    "early_elementary",
    "upper_elementary",
    "middle_school",
    "high_school",
    "college",
    "adult",
    "mixed",
]
ClassReadingLevel = Literal["below_grade", "on_grade", "above_grade", "mixed"]
ClassLanguageSupport = Literal["none", "some_ell", "many_ell"]
ClassConfidence = Literal["low", "mixed", "high"]
ClassPriorKnowledge = Literal["new_topic", "some_background", "reviewing"]
ClassPacing = Literal["short_chunks", "normal", "can_handle_longer"]
ClassLearningPreference = Literal[
    "visual",
    "step_by_step",
    "discussion",
    "hands_on",
    "independent",
    "challenge",
]

GRADE_BAND_BY_LEVEL: dict[TeacherGradeLevel, TeacherGradeBand] = {
    "pre_k": "early_elementary",
    "kindergarten": "early_elementary",
    "grade_1": "early_elementary",
    "grade_2": "early_elementary",
    "grade_3": "upper_elementary",
    "grade_4": "upper_elementary",
    "grade_5": "upper_elementary",
    "grade_6": "middle_school",
    "grade_7": "middle_school",
    "grade_8": "middle_school",
    "grade_9": "high_school",
    "grade_10": "high_school",
    "grade_11": "high_school",
    "grade_12": "high_school",
    "college": "college",
    "adult": "adult",
    "mixed": "mixed",
}


class ClassProfile(BaseModel):
    reading_level: ClassReadingLevel = "mixed"
    language_support: ClassLanguageSupport = "none"
    confidence: ClassConfidence = "mixed"
    prior_knowledge: ClassPriorKnowledge = "some_background"
    pacing: ClassPacing = "normal"
    learning_preferences: list[ClassLearningPreference] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def _trim_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("learning_preferences")
    @classmethod
    def _dedupe_learning_preferences(
        cls,
        value: list[ClassLearningPreference],
    ) -> list[ClassLearningPreference]:
        return list(dict.fromkeys(value))


class TeacherBrief(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=160)
    subtopics: list[str] = Field(min_length=1, max_length=4)
    grade_level: TeacherGradeLevel
    grade_band: TeacherGradeBand
    class_profile: ClassProfile = Field(default_factory=ClassProfile)
    learner_context: str = Field(min_length=1, max_length=1000)
    intended_outcome: TeacherBriefOutcome
    resource_type: TeacherBriefResourceType
    supports: list[TeacherBriefSupport] = Field(default_factory=list)
    depth: TeacherBriefDepth
    teacher_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("subject", "topic", "learner_context", "teacher_notes")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("subtopics")
    @classmethod
    def _normalize_subtopics(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        deduped = list(dict.fromkeys(normalized))
        if not deduped:
            raise ValueError("subtopics must include at least one subtopic.")
        return deduped

    @field_validator("supports")
    @classmethod
    def _dedupe_supports(
        cls, value: list[TeacherBriefSupport]
    ) -> list[TeacherBriefSupport]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _validate_required_text(self) -> "TeacherBrief":
        for field_name in ("subject", "topic", "learner_context"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must not be empty.")
        if not self.subtopics:
            raise ValueError("subtopics must not be empty.")
        self.grade_band = GRADE_BAND_BY_LEVEL[self.grade_level]
        return self


class TopicResolutionRequest(BaseModel):
    raw_topic: str = Field(min_length=1, max_length=200)
    grade_level: TeacherGradeLevel
    grade_band: TeacherGradeBand
    learner_context: str | None = Field(default=None, max_length=1000)
    class_profile: ClassProfile | None = None

    @field_validator("raw_topic", "learner_context")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class TopicResolutionSubtopic(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=240)
    likely_grade_band: str | None = Field(default=None, max_length=80)

    @field_validator("id", "title", "description", "likely_grade_band")
    @classmethod
    def _trim_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class TopicResolutionResult(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=160)
    candidate_subtopics: list[TopicResolutionSubtopic] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_message: str | None = Field(default=None, max_length=240)

    @field_validator("subject", "topic", "clarification_message")
    @classmethod
    def _trim_result_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class ValidationMessage(BaseModel):
    field: str | None = None
    message: str = Field(min_length=1, max_length=240)

    @field_validator("field", "message")
    @classmethod
    def _trim_message_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class ValidationSuggestion(BaseModel):
    field: str = Field(min_length=1, max_length=80)
    suggestion: str = Field(min_length=1, max_length=240)

    @field_validator("field", "suggestion")
    @classmethod
    def _trim_suggestion_fields(cls, value: str) -> str:
        return value.strip()


class BriefValidationRequest(BaseModel):
    brief: TeacherBrief


class BriefValidationResult(BaseModel):
    is_ready: bool
    blockers: list[ValidationMessage] = Field(default_factory=list)
    warnings: list[ValidationMessage] = Field(default_factory=list)
    suggestions: list[ValidationSuggestion] = Field(default_factory=list)


class BriefReviewRequest(BaseModel):
    brief: TeacherBrief


class BriefReviewWarning(BaseModel):
    message: str = Field(min_length=1, max_length=280)
    suggestion: str | None = Field(default=None, max_length=280)

    @field_validator("message", "suggestion")
    @classmethod
    def _trim_review_warning(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BriefReviewResult(BaseModel):
    coherent: bool
    warnings: list[BriefReviewWarning] = Field(default_factory=list)
