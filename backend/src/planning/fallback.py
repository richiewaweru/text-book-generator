from __future__ import annotations

from uuid import uuid4

from planning.models import (
    GenerationDirectives,
    PlanningGenerationSpec,
    PlanningSectionPlan,
    PlanningTemplateContract,
    StudioBriefRequest,
    TemplateDecision,
)


def build_fallback_spec(
    *,
    brief: StudioBriefRequest,
    contract: PlanningTemplateContract,
) -> PlanningGenerationSpec:
    spec_id = uuid4().hex
    return PlanningGenerationSpec(
        id=spec_id,
        template_id=contract.id,
        template_decision=TemplateDecision(
            chosen_id=contract.id,
            chosen_name=contract.name,
            rationale=f"{contract.name} is the safest default when planning needs to fall back.",
            fit_score=0.5,
            alternatives=[],
        ),
        lesson_rationale="This fallback keeps the lesson compact and easy to review before generation.",
        directives=GenerationDirectives(
            tone_profile=brief.preferences.tone,
            reading_level=brief.preferences.reading_level,
            explanation_style=brief.preferences.explanation_style,
            example_style=brief.preferences.example_style,
            scaffold_level="medium",
            brevity=brief.preferences.brevity,
        ),
        committed_budgets=contract.component_budget,
        sections=[
            PlanningSectionPlan(
                id="section-intro",
                order=1,
                role="intro",
                title="Introduction",
                objective="Set the lesson up clearly.",
                selected_components=["hook-hero"],
                rationale="Starts with a focused introduction.",
            ),
            PlanningSectionPlan(
                id="section-explain",
                order=2,
                role="explain",
                title="Explanation",
                objective="Explain the central idea plainly.",
                selected_components=["explanation-block"],
                rationale="Provides the core explanation in the middle of the lesson.",
            ),
            PlanningSectionPlan(
                id="section-summary",
                order=3,
                role="summary",
                title="Summary",
                objective="Close the lesson and point to what comes next.",
                selected_components=["what-next-bridge"],
                rationale="Closes the arc cleanly.",
            ),
        ],
        warning="Planning used defaults - please review and adjust before generating.",
        source_brief_id=brief.source_brief_id(),
        source_brief=brief,
        status="draft",
    )
