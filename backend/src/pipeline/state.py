"""
pipeline.state

The single state object that flows through the LangGraph pipeline.

Field ownership rules (enforced by convention):
    curriculum_planner    → curriculum_outline, style_context
    content_generator     → generated_sections
    diagram_generator     → generated_sections[id].diagram
    interaction_decider   → interaction_specs
    interaction_generator → generated_sections[id].simulation
    section_assembler     → assembled_sections, qc_reports (capacity warnings)
    qc_agent              → qc_reports (semantic issues)

Annotated[list, operator.add] = append-only (LangGraph reducer).
Plain fields = last-write-wins.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field

from pipeline.types.section_content import InteractionSpec, SectionContent
from pipeline.types.template_contract import TemplateContractSummary
from pipeline.types.requests import PipelineRequest, SectionPlan


def _merge_dicts(left: dict, right: dict) -> dict:
    """LangGraph reducer: merge dicts from concurrent fan-out writes."""
    return {**left, **right}


# ── PIPELINE STATUS ──────────────────────────────────────────────────────────

class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


# ── STYLE CONTEXT ────────────────────────────────────────────────────────────

class StyleContext(BaseModel):
    preset_id: str
    palette: str
    surface_style: str
    density: str
    typography: str

    template_id: str
    template_family: str
    interaction_level: str

    grade_band: str
    learner_fit: str

    def diagram_complexity(self) -> str:
        if self.grade_band == 'primary' or self.learner_fit == 'scaffolded':
            return 'simplified'
        if self.grade_band == 'advanced' or self.learner_fit == 'advanced':
            return 'detailed'
        return 'standard'


# ── ERROR AND RETRY TYPES ────────────────────────────────────────────────────

class PipelineError(BaseModel):
    node: str
    message: str
    section_id: Optional[str] = None
    recoverable: bool = True


class RerenderRequest(BaseModel):
    section_id: str
    reason: str
    block_type: str
    auto_fix: Optional[str] = None


class QCReport(BaseModel):
    section_id: str
    passed: bool
    issues: list[dict]
    warnings: list[str]


# ── PIPELINE STATE ───────────────────────────────────────────────────────────

class TextbookPipelineState(BaseModel):

    # ── INPUT — set once at pipeline start ───────────────────────────────────
    request: PipelineRequest
    contract: TemplateContractSummary

    # ── SET BY curriculum_planner ────────────────────────────────────────────
    curriculum_outline: Optional[list[SectionPlan]] = None
    style_context: Optional[StyleContext] = None

    # ── PER-SECTION WORKING STATE ────────────────────────────────────────────
    current_section_id: Optional[str] = None
    current_section_plan: Optional[SectionPlan] = None

    # ── NODE OUTPUTS ─────────────────────────────────────────────────────────
    generated_sections: Annotated[dict[str, SectionContent], _merge_dicts] = Field(
        default_factory=dict
    )
    interaction_specs: Annotated[dict[str, InteractionSpec], _merge_dicts] = Field(
        default_factory=dict
    )
    assembled_sections: Annotated[dict[str, SectionContent], _merge_dicts] = Field(
        default_factory=dict
    )
    qc_reports: Annotated[dict[str, QCReport], _merge_dicts] = Field(
        default_factory=dict
    )

    # ── QC RETRY ─────────────────────────────────────────────────────────────
    rerender_requests: Annotated[list[RerenderRequest], operator.add] = Field(
        default_factory=list
    )
    rerender_count: Annotated[dict[str, int], _merge_dicts] = Field(default_factory=dict)
    max_rerenders: int = 2

    # ── TRACKING ─────────────────────────────────────────────────────────────
    completed_nodes: Annotated[list[str], operator.add] = Field(default_factory=list)
    errors: Annotated[list[PipelineError], operator.add] = Field(default_factory=list)

    status: PipelineStatus = PipelineStatus.PENDING

    # ── HELPERS ──────────────────────────────────────────────────────────────

    @classmethod
    def parse(cls, raw: "TextbookPipelineState | dict") -> "TextbookPipelineState":
        """Convert LangGraph's dict state into a typed model instance."""
        if isinstance(raw, cls):
            return raw
        return cls.model_validate(raw)

    def has_errors_for(self, section_id: str) -> bool:
        return any(e.section_id == section_id for e in self.errors)

    def rerender_count_for(self, section_id: str) -> int:
        return self.rerender_count.get(section_id, 0)

    def can_rerender(self, section_id: str) -> bool:
        return self.rerender_count_for(section_id) < self.max_rerenders
