from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
