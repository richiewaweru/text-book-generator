from __future__ import annotations

from planning.models import PlanningSectionRole

ROLE_COMPONENT_MAP: dict[PlanningSectionRole, tuple[str, ...]] = {
    "intro": ("hook-hero", "callout-block", "key-fact"),
    "explain": (
        "explanation-block",
        "definition-card",
        "worked-example-card",
        "glossary-strip",
        "key-fact",
    ),
    "practice": (
        "practice-stack",
        "student-textbox",
        "short-answer",
        "fill-in-blank",
        "reflection-prompt",
    ),
    "summary": ("summary-block", "what-next-bridge", "reflection-prompt"),
    "process": ("process-steps", "worked-example-card", "explanation-block"),
    "compare": ("comparison-grid", "definition-family", "insight-strip", "diagram-compare"),
    "timeline": ("timeline-block", "explanation-block", "reflection-prompt"),
    "visual": ("diagram-block", "diagram-series", "diagram-compare", "simulation-block"),
    "discover": ("simulation-block", "diagram-block", "callout-block", "explanation-block"),
}

TEMPLATE_ROLE_TO_SECTION_ROLE: dict[str, PlanningSectionRole] = {
    "introduce": "intro",
    "explain": "explain",
    "model": "process",
    "practice": "practice",
    "check": "summary",
    "reflect": "summary",
    "visualize": "visual",
    "vocabulary": "explain",
    "compare": "compare",
    "timeline": "timeline",
    "challenge": "practice",
    "example": "explain",
    "analogy": "explain",
    "misconception": "explain",
    "hint": "practice",
    "answer_check": "summary",
    "self_assess": "summary",
    "question_set": "practice",
    "short_response": "practice",
    "answer_key": "summary",
    "rubric": "summary",
    "visual_prompt": "visual",
}

OUTCOME_ROLE_MAP: dict[str, tuple[str, ...]] = {
    "understand": ("introduce", "explain", "check"),
    "practice": ("model", "practice", "check"),
    "review": ("introduce", "explain", "check"),
    "assess": ("question_set", "short_response", "answer_key"),
    "compare": ("compare", "explain", "check"),
    "vocabulary": ("introduce", "vocabulary", "check"),
}

SUPPORT_ROLE_MAP: dict[str, tuple[str, ...]] = {
    "visuals": ("visualize",),
    "vocabulary_support": ("vocabulary",),
    "worked_examples": ("model", "example"),
    "step_by_step": ("model", "hint"),
    "discussion_questions": ("reflect",),
    "simpler_reading": ("introduce", "explain"),
    "challenge_questions": ("challenge",),
}

VISUAL_COMPONENTS = {"diagram-block", "diagram-series", "diagram-compare", "simulation-block"}
PRACTICE_COMPONENTS = {"practice-stack", "student-textbox", "short-answer", "fill-in-blank"}
CHECK_COMPONENTS = {"reflection-prompt", "what-next-bridge", "short-answer", "fill-in-blank"}
ASSESSMENT_COMPONENTS = {"practice-stack", "student-textbox", "short-answer", "fill-in-blank"}


def components_for_role(role: PlanningSectionRole) -> list[str]:
    return list(ROLE_COMPONENT_MAP.get(role, ()))
