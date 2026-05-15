from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from learning.brief_types import (
    GRADE_BAND_BY_LEVEL,
    ClassProfile,
    TeacherBriefDepth,
    TeacherBriefOutcome,
    TeacherBriefSupport,
    TeacherGradeBand,
    TeacherGradeLevel,
)


LearningJobType = Literal["introduce", "practice", "reteach", "assess", "differentiate"]
PackStatus = Literal["pending", "running", "complete", "failed"]
ResourcePhase = Literal["pending", "planning", "queued", "generating", "done", "failed"]


# Internal intermediate type for pack planning and generation orchestration.
class LearningJob(BaseModel):
    job: LearningJobType
    subject: str
    topic: str
    grade_level: str
    grade_band: str
    objective: str
    class_signals: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommended_depth: Literal["quick", "standard", "deep"] = "standard"
    inferred_supports: list[str] = Field(default_factory=list)
    inferred_class_profile: dict = Field(default_factory=dict)


class PackBriefRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    topic: str = Field(min_length=1, max_length=160)
    subtopics: list[str] = Field(min_length=1, max_length=4)
    grade_level: TeacherGradeLevel
    grade_band: TeacherGradeBand
    class_profile: ClassProfile = Field(default_factory=ClassProfile)
    learner_context: str = Field(min_length=1, max_length=1000)
    intended_outcome: TeacherBriefOutcome
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
    def _validate_required_text(self) -> "PackBriefRequest":
        for field_name in ("subject", "topic", "learner_context"):
            if not getattr(self, field_name):
                raise ValueError(f"{field_name} must not be empty.")
        if not self.subtopics:
            raise ValueError("subtopics must not be empty.")
        self.grade_band = GRADE_BAND_BY_LEVEL[self.grade_level]
        return self


class PackLearningPlan(BaseModel):
    objective: str
    success_criteria: list[str] = Field(default_factory=list)
    prerequisite_skills: list[str] = Field(default_factory=list)
    likely_misconceptions: list[str] = Field(default_factory=list)
    shared_vocabulary: list[str] = Field(default_factory=list)
    shared_examples: list[str] = Field(default_factory=list)


class ResourcePlan(BaseModel):
    id: str
    order: int
    resource_type: str
    intended_outcome: str
    label: str
    purpose: str
    depth: Literal["quick", "standard", "deep"]
    supports: list[str] = Field(default_factory=list)
    enabled: bool = True


class LearningPackPlan(BaseModel):
    pack_id: str
    learning_job: LearningJob
    pack_learning_plan: PackLearningPlan
    resources: list[ResourcePlan]
    pack_rationale: str


class PackGenerateRequest(BaseModel):
    pack_plan: LearningPackPlan
    learner_context: str = Field(min_length=5, max_length=2000)


class PackGenerateResponse(BaseModel):
    pack_id: str
    status: PackStatus


class ResourceStatus(BaseModel):
    resource_id: str
    generation_id: str | None = None
    label: str
    resource_type: str
    status: str
    phase: ResourcePhase


class PackStatusResponse(BaseModel):
    pack_id: str
    status: PackStatus
    learning_job_type: str
    subject: str
    topic: str
    resource_count: int
    completed_count: int
    current_phase: str | None = None
    current_resource_label: str | None = None
    resources: list[ResourceStatus] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None

