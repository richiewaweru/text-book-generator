from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from pipeline.api import PipelineIssue
from pipeline.state import NodeFailureDetail


class GenerationReportLLMAttempt(BaseModel):
    node: str
    attempt: int
    slot: str
    family: str | None = None
    model_name: str | None = None
    endpoint_host: str | None = None
    status: Literal["started", "succeeded", "failed"] = "started"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: float | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    thinking_tokens: int | None = None
    cost_usd: float | None = None
    retryable: bool | None = None
    error: str | None = None


class GenerationReportNode(BaseModel):
    node: str
    scope: Literal["generation", "section"]
    attempt: int | None = None
    status: Literal["running", "succeeded", "failed"] = "running"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: float | None = None
    error: str | None = None
    llm_calls: list[GenerationReportLLMAttempt] = Field(default_factory=list)


class GenerationReportRetry(BaseModel):
    reason: str
    block_type: str
    next_attempt: int
    max_attempts: int
    queued_at: datetime


class GenerationReportFieldRegenAttempt(BaseModel):
    field: str
    outcome: Literal["success", "failed"]
    error: str | None = None


class MediaDecisionTrace(BaseModel):
    slot_id: str
    slot_type: str
    preferred_render_initial: str
    preferred_render_final: str
    fallback_render: str | None = None
    decision_source: Literal[
        "slot_type_default",
        "intelligent_image_prompt",
        "style_context",
    ]
    decision_reason: str | None = None
    intelligent_prompt_resolved: bool = False
    executor_selected: Literal[
        "diagram_generator",
        "image_generator",
        "interaction_generator",
    ] | None = None
    svg_generation_mode: str | None = None
    model_slot: str | None = None
    diagram_kind: str | None = None
    sanitized: bool = False
    intent_validated: bool = False
    svg_failure_reason: str | None = None
    status: Literal["planned", "generated", "failed", "skipped"] = "planned"


class GenerationReportSection(BaseModel):
    section_id: str
    title: str | None = None
    position: int | None = None
    status: Literal["planned", "running", "retry_queued", "ready", "failed", "stalled"] = (
        "planned"
    )
    attempt_count: int = 0
    current_attempt: int | None = None
    first_started_at: datetime | None = None
    completed_at: datetime | None = None
    latency_ms: float | None = None
    expected_components: list[str] = Field(default_factory=list)
    delivered_components: list[str] = Field(default_factory=list)
    missing_components: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[PipelineIssue] = Field(default_factory=list)
    queued_retries: list[GenerationReportRetry] = Field(default_factory=list)
    validation_repair_attempts: int = 0
    validation_repair_successes: int = 0
    media_slots_planned: int = 0
    media_slots_ready: int = 0
    media_slots_failed: int = 0
    visual_placements_count: int = 0
    visual_placements_summary: list[str] = Field(default_factory=list)
    slot_render_modes: dict[str, str] = Field(default_factory=dict)
    media_decisions: list[MediaDecisionTrace] = Field(default_factory=list)
    media_frame_retry_count: int = 0
    media_blocked: bool = False
    media_block_reason: str | None = None
    diagram_outcome: Literal["success", "timeout", "error", "skipped"] | None = None
    image_outcome: Literal["success", "timeout", "error", "skipped"] | None = None
    image_error: str | None = None
    image_provider: str | None = None
    simulation_outcome: Literal["generated", "skipped", "failed"] | None = None
    simulation_failure_reason: str | None = None
    simulation_type_selected: str | None = None
    simulation_goal_selected: str | None = None
    interaction_outcome: Literal["generated", "skipped"] | None = None
    interaction_skip_reason: str | None = None
    interaction_count: int = 0
    interaction_retry_count: int = 0
    field_regen_attempts: list[GenerationReportFieldRegenAttempt] = Field(
        default_factory=list
    )
    failure_detail: NodeFailureDetail | None = None
    final_error: str | None = None
    nodes: list[GenerationReportNode] = Field(default_factory=list)


class GenerationReportOutlineSection(BaseModel):
    section_id: str
    title: str
    position: int
    role: str
    focus: str
    terms_to_define: list[str] = Field(default_factory=list)
    terms_assumed: list[str] = Field(default_factory=list)
    practice_target: str | None = None
    visual_placements_count: int = 0
    required_components: list[str] = Field(default_factory=list)


class GenerationPlannerTraceSection(BaseModel):
    section_id: str
    title: str
    position: int
    role: str
    rationale_summary: str
    visual_placements_count: int = 0
    visual_placements_summary: list[str] = Field(default_factory=list)


class GenerationPlannerTrace(BaseModel):
    path: Literal["fresh", "seeded_enrichment", "seeded_passthrough"]
    result: Literal["planned", "enriched", "fallback", "seeded_passthrough"]
    duplicate_term_warnings: list[str] = Field(default_factory=list)
    sections: list[GenerationPlannerTraceSection] = Field(default_factory=list)


class GenerationReportSummary(BaseModel):
    planned_sections: int = 0
    ready_sections: int = 0
    missing_sections: int = 0
    failed_sections: int = 0
    stalled_sections: int = 0
    sections_with_planned_visuals: int = 0
    retry_count: int = 0
    llm_transport_retries: int = 0
    validation_repair_attempts: int = 0
    validation_repair_successes: int = 0
    qc_rerenders: int = 0
    media_slots_planned: int = 0
    media_slots_ready: int = 0
    media_slots_failed: int = 0
    media_frame_retry_count: int = 0
    simulation_success_count: int = 0
    simulation_failure_count: int = 0
    image_provider_counts: dict[str, int] = Field(default_factory=dict)
    diagram_retries: int = 0
    diagram_timeout_count: int = 0
    sections_without_media: int = 0
    planned_image_slots: int = 0
    planned_svg_slots: int = 0
    planned_simulation_slots: int = 0
    svg_attempted_slots: int = 0
    svg_success_slots: int = 0
    svg_failed_slots: int = 0
    raw_svg_generation_count: int = 0
    svg_sanitizer_failure_count: int = 0
    svg_validation_failure_count: int = 0
    svg_intent_retry_count: int = 0
    svg_generation_model_slot: str | None = None
    svg_diagram_kind_counts: dict[str, int] = Field(default_factory=dict)
    image_attempted_slots: int = 0
    image_success_slots: int = 0
    image_failed_slots: int = 0
    image_success_count: int = 0
    image_failure_count: int = 0
    image_slots_count: int = 0
    svg_slots_count: int = 0
    interaction_skip_count: int = 0
    interaction_retry_count: int = 0
    prompt_builder_calls: int = 0
    field_regen_count: int = 0
    field_regen_success_count: int = 0
    warning_count: int = 0
    blocking_issue_count: int = 0
    total_llm_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float | None = None
    slowest_node: str | None = None
    slowest_node_latency_ms: float | None = None
    slowest_section: str | None = None
    slowest_section_latency_ms: float | None = None


class GenerationTimelineEvent(BaseModel):
    sequence: int
    type: str
    timestamp: datetime
    node: str | None = None
    section_id: str | None = None
    attempt: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class GenerationReport(BaseModel):
    generation_id: str
    subject: str
    context: str
    mode: str | None = None
    template_id: str
    preset_id: str
    source_generation_id: str | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    outcome: Literal["full", "partial", "failed"] | None = None
    section_count: int | None = None
    quality_passed: bool | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    wall_time_seconds: float | None = None
    generation_time_seconds: float | None = None
    final_error: str | None = None
    summary: GenerationReportSummary = Field(default_factory=GenerationReportSummary)
    runtime_curriculum_outline: list[GenerationReportOutlineSection] = Field(default_factory=list)
    planner_trace: GenerationPlannerTrace | None = None
    sections: list[GenerationReportSection] = Field(default_factory=list)
    generation_nodes: list[GenerationReportNode] = Field(default_factory=list)
    timeline: list[GenerationTimelineEvent] = Field(default_factory=list)
    coherence_review: dict[str, Any] | None = None
    pipeline_version: Literal["v2", "v3"] = "v2"

    @field_validator(
        "started_at",
        "completed_at",
        mode="before",
    )
    @classmethod
    def _normalize_utc(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
