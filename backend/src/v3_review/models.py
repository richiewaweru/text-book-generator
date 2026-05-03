from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["minor", "major", "blocking"]

RepairExecutor = Literal[
    "section_writer",
    "question_writer",
    "visual_executor",
    "answer_key_generator",
    "assembler",
]

IssueCategory = Literal[
    "missing_planned_content",
    "extra_unplanned_content",
    "anchor_drift",
    "visual_mismatch",
    "question_mismatch",
    "answer_key_mismatch",
    "register_mismatch",
    "practice_progression_mismatch",
    "internal_artifact_leak",
    "schema_violation",
    "print_risk",
]

CoherenceStatus = Literal[
    "passed",
    "passed_with_warnings",
    "repair_required",
    "failed",
    "escalated",
]


class ReviewIssue(BaseModel):
    model_config = {"extra": "forbid"}

    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: Severity
    category: IssueCategory
    message: str
    blueprint_ref: str | None = None
    generated_ref: str | None = None
    suggested_repair_executor: RepairExecutor
    repair_target_id: str | None = None


class RepairTarget(BaseModel):
    model_config = {"extra": "forbid"}

    target_id: str
    executor: RepairExecutor
    source_work_order_id: str | None = None
    target_type: Literal[
        "section_component",
        "question",
        "visual",
        "answer_key",
        "assembly",
    ]
    target_ref: str
    section_id: str | None = None
    component_id: str | None = None
    question_id: str | None = None
    visual_id: str | None = None
    reason: str
    constraints: list[str] = Field(default_factory=list)
    severity: Severity


class CoherenceReport(BaseModel):
    model_config = {"extra": "forbid"}

    blueprint_id: str
    generation_id: str
    status: CoherenceStatus
    deterministic_passed: bool
    llm_review_passed: bool
    blocking_count: int = 0
    major_count: int = 0
    minor_count: int = 0
    issues: list[ReviewIssue] = Field(default_factory=list)
    repair_targets: list[RepairTarget] = Field(default_factory=list)
    repaired_target_ids: list[str] = Field(default_factory=list)
    repair_attempts: dict[str, int] = Field(default_factory=dict)


class RepairOutcome(BaseModel):
    model_config = {"extra": "forbid"}

    target_id: str
    ok: bool
    attempt: int
    new_block: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    # Typed payloads for apply_repair (Proposal 2 blocks); omitted from JSON summary when empty.
    component_blocks: list[Any] = Field(default_factory=list)
    question_blocks: list[Any] = Field(default_factory=list)
    visual_blocks: list[Any] = Field(default_factory=list)
    answer_key_block: Any | None = None

    @field_validator("attempt")
    @classmethod
    def _attempt_range(cls, v: int) -> int:
        if v not in (1, 2):
            msg = "attempt must be 1 or 2"
            raise ValueError(msg)
        return v


def derive_coherence_status(
    issues: Sequence[ReviewIssue],
    repair_targets: Sequence[RepairTarget],
) -> CoherenceStatus:
    blocking = [i for i in issues if i.severity == "blocking"]
    major = [i for i in issues if i.severity == "major"]
    minor = [i for i in issues if i.severity == "minor"]
    if not blocking and not major and not minor:
        return "passed"
    if not blocking and not major:
        return "passed_with_warnings"
    if (blocking or major) and repair_targets:
        return "repair_required"
    return "failed"


def refresh_issue_counts(report: CoherenceReport) -> None:
    blocking = [i for i in report.issues if i.severity == "blocking"]
    major = [i for i in report.issues if i.severity == "major"]
    minor = [i for i in report.issues if i.severity == "minor"]
    report.blocking_count = len(blocking)
    report.major_count = len(major)
    report.minor_count = len(minor)


__all__ = [
    "CoherenceReport",
    "CoherenceStatus",
    "IssueCategory",
    "RepairExecutor",
    "RepairOutcome",
    "RepairTarget",
    "ReviewIssue",
    "Severity",
    "derive_coherence_status",
    "refresh_issue_counts",
]
