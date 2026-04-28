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


class TeacherBrief(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=160)
    subtopics: list[str] = Field(min_length=1, max_length=4)
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
        return self


class TopicResolutionRequest(BaseModel):
    raw_topic: str = Field(min_length=1, max_length=200)
    learner_context: str | None = Field(default=None, max_length=1000)

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
