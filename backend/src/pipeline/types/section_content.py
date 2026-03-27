"""
pipeline.types.section_content

Python mirror of Lectio's src/lib/types.ts.

The JSON produced by SectionContent.model_dump_json() must be valid input
to the Lectio frontend's TypeScript SectionContent type. Every field name,
every optional marker, every nested type must match types.ts exactly.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── SHARED PRIMITIVES ────────────────────────────────────────────────────────

Difficulty = Literal['warm', 'medium', 'cold', 'extension']
GradeBand = Literal['primary', 'secondary', 'advanced']
HintLevel = Literal[1, 2, 3]


# ── GROUP 1 — FOUNDATION ────────────────────────────────────────────────────

class LevelPill(BaseModel):
    label: str
    variant: Literal['all', 'warm', 'medium', 'cold']


class SectionHeaderContent(BaseModel):
    title: str
    subject: str
    grade_band: GradeBand
    subtitle: Optional[str] = None
    section_number: Optional[str] = None
    objective: Optional[str] = None
    level_pills: Optional[list[LevelPill]] = None


class HookHeroContent(BaseModel):
    headline: str
    body: str
    anchor: str
    type: Literal['prose', 'quote', 'question', 'data-point'] = 'prose'
    svg_content: Optional[str] = None
    quote_attribution: Optional[str] = None
    question_options: Optional[list[str]] = None
    data_point: Optional[dict] = None


class ExplanationCallout(BaseModel):
    type: Literal['remember', 'insight', 'sidenote']
    text: str


class ExplanationContent(BaseModel):
    body: str
    emphasis: list[str]
    callouts: Optional[list[ExplanationCallout]] = None


class PrerequisiteItem(BaseModel):
    concept: str
    refresher: Optional[str] = None


class PrerequisiteContent(BaseModel):
    items: list[PrerequisiteItem]
    label: Optional[str] = None


class WhatNextContent(BaseModel):
    body: str
    next: str
    preview: Optional[str] = None
    prerequisites: Optional[list[str]] = None


class InterviewContent(BaseModel):
    prompt: str
    audience: str
    follow_up: Optional[str] = None


# ── GROUP 2 — DEFINITION AND KNOWLEDGE ──────────────────────────────────────

class DefinitionContent(BaseModel):
    term: str
    formal: str
    plain: str
    etymology: Optional[str] = None
    notation: Optional[str] = None
    related_terms: Optional[list[str]] = None
    symbol: Optional[str] = None
    examples: Optional[list[str]] = None


class DefinitionFamilyContent(BaseModel):
    family_title: str
    definitions: list[DefinitionContent]
    family_intro: Optional[str] = None


class GlossaryTerm(BaseModel):
    term: str
    definition: str
    used_in: Optional[str] = None
    pronunciation: Optional[str] = None
    related: Optional[list[str]] = None


class GlossaryContent(BaseModel):
    terms: list[GlossaryTerm]


class InsightCell(BaseModel):
    label: str
    value: str
    note: Optional[str] = None
    highlight: Optional[bool] = None


class InsightStripContent(BaseModel):
    cells: list[InsightCell]


class ComparisonColumn(BaseModel):
    id: str
    title: str
    summary: str
    badge: Optional[str] = None
    detail: Optional[str] = None
    highlight: Optional[bool] = None


class ComparisonRow(BaseModel):
    criterion: str
    values: list[str]
    takeaway: Optional[str] = None


class ComparisonGridContent(BaseModel):
    title: str
    columns: list[ComparisonColumn]
    rows: list[ComparisonRow]
    intro: Optional[str] = None
    apply_prompt: Optional[str] = None


# ── GROUP 3 — EXAMPLES AND PROCESS ──────────────────────────────────────────

class WorkedStep(BaseModel):
    label: str
    content: str
    note: Optional[str] = None
    formula: Optional[str] = None
    diagram_ref: Optional[str] = None


class WorkedExampleContent(BaseModel):
    title: str
    setup: str
    steps: list[WorkedStep]
    conclusion: str
    method_label: Optional[str] = None
    alternative: Optional['WorkedExampleContent'] = None
    answer: Optional[str] = None
    alternatives: Optional[list[str]] = None


class ProcessStepItem(BaseModel):
    number: int
    action: str
    detail: str
    input: Optional[str] = None
    output: Optional[str] = None
    warning: Optional[str] = None


class ProcessContent(BaseModel):
    title: str
    steps: list[ProcessStepItem]
    intro: Optional[str] = None
    checklist_mode: Optional[bool] = None


# ── GROUP 4 — ASSESSMENT AND PRACTICE ───────────────────────────────────────

class PracticeHint(BaseModel):
    level: HintLevel
    text: str


class PracticeSolution(BaseModel):
    approach: str
    answer: str
    worked: Optional[str] = None


class PracticeProblem(BaseModel):
    difficulty: Difficulty
    question: str
    hints: list[PracticeHint]
    solution: Optional[PracticeSolution] = None
    writein_lines: Optional[int] = None
    self_assess: Optional[bool] = None
    context: Optional[str] = None


class PracticeContent(BaseModel):
    problems: list[PracticeProblem]
    hints_visible_default: bool = False
    solutions_available: bool = False
    label: Optional[str] = None


class QuizOption(BaseModel):
    text: str
    correct: bool
    explanation: str


class QuizContent(BaseModel):
    question: str
    options: list[QuizOption]
    feedback_correct: str
    feedback_incorrect: str
    show_explanations: Optional[bool] = None


class ReflectionContent(BaseModel):
    prompt: str
    type: Literal[
        'open', 'pair-share', 'sentence-stem',
        'timed', 'connect', 'predict', 'transfer'
    ]
    space: Optional[int] = None
    sentence_stem: Optional[str] = None
    time_minutes: Optional[int] = None
    pair_instruction: Optional[str] = None


# ── GROUP 5 — ALERTS ────────────────────────────────────────────────────────

class PitfallContent(BaseModel):
    misconception: str
    correction: str
    example: Optional[str] = None
    severity: Literal['minor', 'major'] = 'major'
    examples: Optional[list[str]] = None
    why: Optional[str] = None


# ── GROUP 6 — DIAGRAMS ──────────────────────────────────────────────────────


class DiagramElement(BaseModel):
    """One visual element in a structured diagram spec."""
    id: str
    label: str
    x: float
    y: float
    width: float = 120
    height: float = 60
    shape: Literal["rect", "circle", "diamond", "rounded-rect"] = "rounded-rect"
    emphasis: bool = False


class DiagramConnection(BaseModel):
    """A directed edge between two diagram elements."""
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: Literal["solid", "dashed", "arrow"] = "arrow"


class DiagramSpec(BaseModel):
    """Structured diagram specification — rendered client-side instead of raw SVG."""
    type: Literal["process-flow", "hierarchy", "compare", "cycle", "concept-map"]
    title: str
    elements: list[DiagramElement]
    connections: list[DiagramConnection] = Field(default_factory=list)
    layout_hint: Literal["horizontal", "vertical", "radial"] = "horizontal"


class DiagramCallout(BaseModel):
    id: str
    x: float
    y: float
    label: str
    explanation: str


class DiagramContent(BaseModel):
    svg_content: str = ""
    spec: Optional[DiagramSpec] = None
    caption: str
    alt_text: str
    zoom_label: Optional[str] = None
    callouts: Optional[list[DiagramCallout]] = None
    figure_number: Optional[int] = None


class DiagramCompareContent(BaseModel):
    before_svg: str
    after_svg: str
    before_label: str
    after_label: str
    caption: str
    alt_text: str
    before_details: Optional[list[str]] = None
    after_details: Optional[list[str]] = None


class DiagramSeriesContent(BaseModel):
    title: str
    diagrams: list[dict]


class TimelineEvent(BaseModel):
    id: str
    year: str
    title: str
    summary: str
    era: Optional[str] = None
    impact: Optional[str] = None
    tags: Optional[list[str]] = None


class TimelineContent(BaseModel):
    title: str
    events: list[TimelineEvent]
    intro: Optional[str] = None
    closing_takeaway: Optional[str] = None


# ── GROUP 7 — SIMULATION ────────────────────────────────────────────────────

SimulationType = Literal[
    'graph_slider', 'probability_tree', 'equation_reveal',
    'geometry_explorer', 'molecule_viewer', 'timeline_scrubber'
]


class InteractionSpec(BaseModel):
    type: SimulationType
    goal: str
    anchor_content: dict
    context: dict
    dimensions: dict
    print_translation: Literal['static_midstate', 'static_diagram', 'hide']


class SimulationContent(BaseModel):
    spec: InteractionSpec
    html_content: Optional[str] = None
    fallback_diagram: Optional[DiagramContent] = None
    explanation: Optional[str] = None


# ── PHASED SUB-SCHEMAS (used by split content_generator) ────────────────────


class CoreContent(BaseModel):
    """Phase 1: Foundation content — required in every section."""

    section_id: str
    template_id: str
    header: SectionHeaderContent
    hook: HookHeroContent
    explanation: ExplanationContent


class PracticePhaseContent(BaseModel):
    """Phase 2: Practice and reinforcement."""

    practice: PracticeContent
    what_next: WhatNextContent
    pitfall: Optional[PitfallContent] = None
    pitfalls: Optional[list[PitfallContent]] = None
    prerequisites: Optional[PrerequisiteContent] = None


class EnrichmentPhaseContent(BaseModel):
    """Phase 3: Optional enrichment components."""

    worked_example: Optional[WorkedExampleContent] = None
    worked_examples: Optional[list[WorkedExampleContent]] = None
    process: Optional[ProcessContent] = None
    definition: Optional[DefinitionContent] = None
    definition_family: Optional[DefinitionFamilyContent] = None
    quiz: Optional[QuizContent] = None
    reflection: Optional[ReflectionContent] = None
    glossary: Optional[GlossaryContent] = None
    comparison_grid: Optional[ComparisonGridContent] = None
    timeline: Optional[TimelineContent] = None
    insight_strip: Optional[InsightStripContent] = None
    interview: Optional[InterviewContent] = None


# ── THE FULL SECTION OBJECT ─────────────────────────────────────────────────

class SectionContent(BaseModel):
    section_id: str
    template_id: str

    # Required
    header: SectionHeaderContent
    hook: HookHeroContent
    explanation: ExplanationContent
    practice: PracticeContent
    what_next: WhatNextContent

    # Optional
    prerequisites: Optional[PrerequisiteContent] = None
    definition: Optional[DefinitionContent] = None
    definition_family: Optional[DefinitionFamilyContent] = None
    worked_example: Optional[WorkedExampleContent] = None
    worked_examples: Optional[list[WorkedExampleContent]] = None
    process: Optional[ProcessContent] = None
    diagram: Optional[DiagramContent] = None
    diagram_compare: Optional[DiagramCompareContent] = None
    diagram_series: Optional[DiagramSeriesContent] = None
    comparison_grid: Optional[ComparisonGridContent] = None
    timeline: Optional[TimelineContent] = None
    insight_strip: Optional[InsightStripContent] = None
    pitfall: Optional[PitfallContent] = None
    pitfalls: Optional[list[PitfallContent]] = None
    quiz: Optional[QuizContent] = None
    reflection: Optional[ReflectionContent] = None
    glossary: Optional[GlossaryContent] = None
    simulation: Optional[SimulationContent] = None
    interview: Optional[InterviewContent] = None

    def to_json(self) -> str:
        """Serialise for the frontend. Omits None fields."""
        return self.model_dump_json(exclude_none=True, indent=2)
