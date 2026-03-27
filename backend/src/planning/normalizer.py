from __future__ import annotations

from planning.models import (
    GenerationDirectives,
    NormalizedBrief,
    PlanningLearningOutcome,
    PlanningScaffoldLevel,
    PlanningTopicType,
    StudioBriefRequest,
)

_PROCESS_HINTS = (
    "how to",
    "steps",
    "process",
    "procedure",
    "method",
    "solve",
    "carry out",
)
_FACT_HINTS = (
    "facts",
    "terms",
    "definitions",
    "vocabulary",
    "dates",
    "names",
    "remember",
)


def _resolve_topic_type(brief: StudioBriefRequest) -> PlanningTopicType:
    if brief.signals.topic_type is not None:
        return brief.signals.topic_type

    intent = brief.intent.lower()
    if any(marker in intent for marker in _PROCESS_HINTS):
        return "process"
    if any(marker in intent for marker in _FACT_HINTS):
        return "facts"
    if " and " in intent or "," in intent:
        return "mixed"
    return "concept"


def _resolve_learning_outcome(
    brief: StudioBriefRequest,
    topic_type: PlanningTopicType,
) -> PlanningLearningOutcome:
    if brief.signals.learning_outcome is not None:
        return brief.signals.learning_outcome
    if topic_type == "process":
        return "be-able-to-do"
    if topic_type == "facts":
        return "remember-terms"
    return "understand-why"


def _resolve_scaffold_level(brief: StudioBriefRequest) -> PlanningScaffoldLevel:
    styles = set(brief.signals.class_style)
    if brief.preferences.reading_level == "simple" or "needs-explanation-first" in styles:
        return "high"
    if brief.preferences.reading_level == "advanced" or "tries-before-told" in styles:
        return "low"
    return "medium"


def _scope_warning(brief: StudioBriefRequest, topic_type: PlanningTopicType) -> str | None:
    intent = brief.intent.strip()
    if len(intent.split()) > 12:
        return "Topic looks broad. Keep the lesson tightly scoped when you review the plan."
    if topic_type == "mixed" and (" and " in intent.lower() or "," in intent):
        return "This topic may contain several sub-topics. Review the section focus before generating."
    return None


def normalize_brief(brief: StudioBriefRequest) -> NormalizedBrief:
    resolved_topic_type = _resolve_topic_type(brief)
    resolved_learning_outcome = _resolve_learning_outcome(brief, resolved_topic_type)
    resolved_format = (
        "printed-booklet" if brief.constraints.print_first else brief.signals.format or "both"
    )
    directives = GenerationDirectives(
        tone_profile=brief.preferences.tone,
        reading_level=brief.preferences.reading_level,
        explanation_style=brief.preferences.explanation_style,
        example_style=brief.preferences.example_style,
        scaffold_level=_resolve_scaffold_level(brief),
        brevity=brief.preferences.brevity,
    )
    keyword_profile = [
        token.strip(" ,.")
        for token in brief.intent.lower().split()
        if len(token.strip(" ,.")) > 3
    ]
    return NormalizedBrief(
        brief=brief,
        resolved_topic_type=resolved_topic_type,
        resolved_learning_outcome=resolved_learning_outcome,
        resolved_format=resolved_format,
        directives=directives,
        scope_warning=_scope_warning(brief, resolved_topic_type),
        keyword_profile=keyword_profile[:12],
    )
