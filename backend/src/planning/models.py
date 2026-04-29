from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from pipeline.types.requests import BlockVisualPlacement, GenerationMode
from pipeline.types.teacher_brief import TeacherBrief

PlanningTone = Literal["supportive", "neutral", "rigorous"]
PlanningReadingLevel = Literal["simple", "standard", "advanced"]
PlanningExplanationStyle = Literal["concrete-first", "concept-first", "balanced"]
PlanningExampleStyle = Literal["everyday", "academic", "exam"]
PlanningBrevity = Literal["tight", "balanced", "expanded"]
PlanningScaffoldLevel = Literal["high", "medium", "low"]
PlanningVisualIntent = Literal[
    "explain_structure",
    "show_realism",
    "demonstrate_process",
    "compare_variants",
]
PlanningVisualMode = Literal["image", "svg"]
PlanningSectionRole = Literal[
    "intro",
    "explain",
    "practice",
    "summary",
    "process",
    "compare",
    "timeline",
    "visual",
    "discover",
]
PlanningSpecStatus = Literal["draft", "reviewed", "committed"]
PlanValidationSeverity = Literal["warning", "blocking"]


class GenerationDirectives(BaseModel):
    tone_profile: PlanningTone
    reading_level: PlanningReadingLevel
    explanation_style: PlanningExplanationStyle
    example_style: PlanningExampleStyle
    scaffold_level: PlanningScaffoldLevel
    brevity: PlanningBrevity


class PlanningTemplateContract(BaseModel):
    id: str
    name: str
    family: str
    intent: str
    tagline: str
    reading_style: str | None = None
    tags: list[str] = Field(default_factory=list)
    best_for: list[str] = Field(default_factory=list)
    not_ideal_for: list[str] = Field(default_factory=list)
    learner_fit: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    interaction_level: str
    lesson_flow: list[str] = Field(default_factory=list)
    required_components: list[str] = Field(default_factory=list)
    optional_components: list[str] = Field(default_factory=list)
    always_present: list[str] = Field(default_factory=list)
    available_components: list[str] = Field(default_factory=list)
    component_budget: dict[str, int] = Field(default_factory=dict)
    max_per_section: dict[str, int] = Field(default_factory=dict)
    default_behaviours: dict[str, str] = Field(default_factory=dict)
    section_role_defaults: dict[PlanningSectionRole, list[str]] = Field(default_factory=dict)
    layout_notes: list[str] = Field(default_factory=list)
    responsive_rules: list[str] = Field(default_factory=list)
    print_rules: list[str] = Field(default_factory=list)
    allowed_presets: list[str] = Field(default_factory=list)
    why_this_template_exists: str = ""
    generation_guidance: dict[str, str | list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _hydrate_legacy_fields(self) -> "PlanningTemplateContract":
        if not self.always_present and self.required_components:
            self.always_present = list(dict.fromkeys(self.required_components))
        if not self.available_components:
            self.available_components = list(
                dict.fromkeys([*self.required_components, *self.optional_components])
            )
        return self


class TemplateAlternative(BaseModel):
    template_id: str
    template_name: str
    fit_score: float = Field(ge=0, le=1)
    why_not_chosen: str


class TemplateDecision(BaseModel):
    chosen_id: str
    chosen_name: str
    rationale: str
    fit_score: float = Field(ge=0, le=1)
    alternatives: list[TemplateAlternative] = Field(default_factory=list)


class VisualPolicy(BaseModel):
    required: bool = False
    intent: PlanningVisualIntent | None = None
    mode: PlanningVisualMode | None = None
    goal: str | None = None
    style_notes: str | None = None

    @model_validator(mode="after")
    def _mode_required_when_visual_required(self) -> "VisualPolicy":
        if self.required and (self.mode is None or self.intent is None):
            raise ValueError("VisualPolicy: mode and intent must be set when required=True")
        return self


class SectionGenerationNotes(BaseModel):
    tone_override: str | None = None
    brevity_override: PlanningBrevity | None = None
    explanation_override: str | None = None


class PlanningSectionPlan(BaseModel):
    id: str
    order: int
    role: PlanningSectionRole
    title: str
    objective: str | None = None
    focus_note: str | None = None
    selected_components: list[str] = Field(default_factory=list)
    visual_policy: VisualPolicy | None = None
    generation_notes: SectionGenerationNotes | None = None
    rationale: str
    bridges_from: str | None = None
    bridges_to: str | None = None
    terms_to_define: list[str] = Field(default_factory=list)
    terms_assumed: list[str] = Field(default_factory=list)
    practice_target: str | None = None
    visual_placements: list[BlockVisualPlacement] = Field(default_factory=list)

    @field_validator(
        "title",
        "objective",
        "focus_note",
        "rationale",
        "bridges_from",
        "bridges_to",
    )
    @classmethod
    def _trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class CompositionResult(BaseModel):
    sections: list[PlanningSectionPlan]
    lesson_rationale: str
    warning: str | None = None


class PlanValidationIssue(BaseModel):
    field: str | None = None
    message: str
    severity: PlanValidationSeverity = "blocking"

    @field_validator("field", "message")
    @classmethod
    def _trim_issue_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PlanValidationResult(BaseModel):
    is_valid: bool
    issues: list[PlanValidationIssue] = Field(default_factory=list)


class PlanningGenerationSpec(BaseModel):
    id: str
    template_id: str
    preset_id: str = "blue-classroom"
    mode: GenerationMode = GenerationMode.BALANCED
    template_decision: TemplateDecision
    lesson_rationale: str
    directives: GenerationDirectives
    committed_budgets: dict[str, int] = Field(default_factory=dict)
    sections: list[PlanningSectionPlan]
    warning: str | None = None
    source_brief_id: str
    source_brief: TeacherBrief
    status: PlanningSpecStatus = "draft"

    @model_validator(mode="after")
    def _validate_sections(self) -> "PlanningGenerationSpec":
        expected = list(range(1, len(self.sections) + 1))
        actual = [section.order for section in self.sections]
        if actual != expected:
            raise ValueError("Section order must be sequential starting at 1.")
        return self
