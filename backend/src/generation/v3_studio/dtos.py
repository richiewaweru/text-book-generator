from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from v3_blueprint.models import ProductionBlueprint


class V3InputForm(BaseModel):
    model_config = {"extra": "forbid"}

    # Step 1 — Basics
    grade_level: str  # e.g. "Grade 9"
    subject: str
    duration_minutes: int = Field(ge=15, le=90)

    # Step 2 — Concept
    topic: str  # raw topic text
    subtopics: list[str] = Field(default_factory=list)  # resolved subtopics
    prior_knowledge: str = ""  # what they've already covered

    # Step 3 — Lesson shape
    lesson_mode: Literal[
        "first_exposure",
        "consolidation",
        "repair",
        "retrieval",
        "transfer",
        "other",
    ] = "first_exposure"
    lesson_mode_other: str = ""  # when lesson_mode == "other"

    intended_outcome: Literal[
        "understand",
        "practise",
        "review",
        "assess",
        "other",
    ] = "understand"
    intended_outcome_other: str = ""  # when intended_outcome == "other"

    # Step 4 — Class profile
    learner_level: Literal["below_grade", "on_grade", "above_grade", "mixed"] = "on_grade"
    reading_level: Literal["below_grade", "on_grade", "above_grade", "mixed"] = "on_grade"
    language_support: Literal["none", "some_ell", "many_ell"] = "none"
    prior_knowledge_level: Literal["new_topic", "some_background", "reviewing"] = "new_topic"

    support_needs: list[str] = Field(default_factory=list)
    learning_preferences: list[
        Literal["visual", "step_by_step", "discussion", "hands_on", "challenge"]
    ] = Field(default_factory=list)

    # Step 5 — Optional intent
    free_text: str = ""  # anything not captured above


class V3SignalSummary(BaseModel):
    model_config = {"extra": "forbid"}

    topic: str
    subtopic: str | None = None
    prior_knowledge: list[str] = Field(default_factory=list)
    learner_needs: list[str] = Field(default_factory=list)
    teacher_goal: str
    inferred_resource_type: str
    confidence: Literal["low", "medium", "high"]
    missing_signals: list[str] = Field(default_factory=list)


class V3ClarificationQuestion(BaseModel):
    model_config = {"extra": "forbid"}

    question: str
    reason: str
    optional: bool = False


class V3ClarificationAnswer(BaseModel):
    model_config = {"extra": "forbid"}

    question: str
    answer: str


class V3AppliedLensDTO(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    label: str
    reason: str
    effects: list[str] = Field(default_factory=list)


class V3ComponentPlanDTO(BaseModel):
    model_config = {"extra": "forbid"}

    component_id: str
    teacher_label: str
    content_intent: str


class V3SectionPlanItemDTO(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    title: str
    order: int
    learning_intent: str
    components: list[V3ComponentPlanDTO] = Field(default_factory=list)
    visual_required: bool = False


class V3QuestionPlanDTO(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    difficulty: Literal["warm", "medium", "cold", "transfer"]
    expected_answer: str
    diagram_required: bool
    attaches_to_section_id: str
    prompt: str = ""


class V3AnchorExampleDTO(BaseModel):
    model_config = {"extra": "forbid"}

    label: str
    facts: dict[str, str] = Field(default_factory=dict)
    correct_result: str | None = None
    reuse_scope: str


class V3LearnerContextDTO(BaseModel):
    model_config = {"extra": "forbid"}

    grade_level: str
    subject: str
    duration_minutes: int
    lesson_mode: str
    learner_level: str
    reading_level: str
    language_support: str
    prior_knowledge_level: str
    support_needs: list[str] = Field(default_factory=list)
    prior_knowledge: str


class BlueprintPreviewDTO(BaseModel):
    model_config = {"extra": "forbid"}

    blueprint_id: str
    resource_type: str
    title: str
    template_id: str = "guided-concept-path"
    lenses: list[V3AppliedLensDTO] = Field(default_factory=list)
    anchor: V3AnchorExampleDTO | None = None
    section_plan: list[V3SectionPlanItemDTO] = Field(default_factory=list)
    question_plan: list[V3QuestionPlanDTO] = Field(default_factory=list)
    register_summary: str = ""
    support_summary: list[str] = Field(default_factory=list)
    learner_context: V3LearnerContextDTO | None = None


class ClarifyRequest(BaseModel):
    model_config = {"extra": "forbid"}

    signals: V3SignalSummary
    form: V3InputForm


class GenerateBlueprintRequest(BaseModel):
    model_config = {"extra": "forbid"}

    signals: V3SignalSummary
    form: V3InputForm
    clarification_answers: list[V3ClarificationAnswer] = Field(default_factory=list)


class AdjustBlueprintRequest(BaseModel):
    model_config = {"extra": "forbid"}

    blueprint_id: str
    adjustment: str


class V3GenerateStartRequest(BaseModel):
    model_config = {"extra": "forbid"}

    generation_id: str
    blueprint_id: str
    template_id: str = "guided-concept-path"
    blueprint: dict[str, Any] | None = None


class V3GenerateStartResponse(BaseModel):
    model_config = {"extra": "forbid"}

    generation_id: str


class V3PdfExportRequest(BaseModel):
    """PDF export for v3 Studio backed by persisted generation documents."""

    model_config = {"extra": "forbid"}

    school_name: str = Field(min_length=1)
    teacher_name: str = Field(min_length=1)
    date: str | None = None
    include_toc: bool = True
    include_answers: bool = True


class V3GenerationHistoryItemDTO(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    subject: str
    title: str
    status: str
    booklet_status: str
    section_count: int
    document_section_count: int
    template_id: str
    created_at: str | None = None
    completed_at: str | None = None


class V3GenerationDetailDTO(BaseModel):
    model_config = {"extra": "forbid"}

    id: str
    subject: str
    title: str
    status: str
    booklet_status: str
    template_id: str
    section_count: int
    document_section_count: int
    report_json: dict[str, Any]
    created_at: str | None = None
    completed_at: str | None = None


class ProductionBlueprintEnvelope(BaseModel):
    """LLM structured output wrapper."""

    model_config = {"extra": "forbid"}

    blueprint: ProductionBlueprint


__all__ = [
    "AdjustBlueprintRequest",
    "BlueprintPreviewDTO",
    "ClarifyRequest",
    "GenerateBlueprintRequest",
    "ProductionBlueprintEnvelope",
    "V3AppliedLensDTO",
    "V3ClarificationAnswer",
    "V3ClarificationQuestion",
    "V3ComponentPlanDTO",
    "V3GenerateStartRequest",
    "V3GenerateStartResponse",
    "V3GenerationDetailDTO",
    "V3GenerationHistoryItemDTO",
    "V3PdfExportRequest",
    "V3InputForm",
    "V3LearnerContextDTO",
    "V3QuestionPlanDTO",
    "V3SectionPlanItemDTO",
    "V3SignalSummary",
]
