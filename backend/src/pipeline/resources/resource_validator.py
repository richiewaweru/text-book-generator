from __future__ import annotations

import re

from pipeline.resources.resource_templates import ResourceTemplate
from pipeline.types.teacher_brief import (
    BriefValidationResult,
    TeacherBrief,
    ValidationMessage,
    ValidationSuggestion,
)

_BROADER_SUBTOPIC_TERMS = {
    "algebra",
    "fractions",
    "photosynthesis",
    "grammar",
    "ecosystems",
    "revolution",
    "main idea",
    "reading comprehension",
}
_STRUGGLING_READER_HINTS = (
    "struggling",
    "below grade",
    "below-grade",
    "low confidence",
    "english learners",
    "ell",
    "el ",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _message(
    *, field: str | None, message: str
) -> ValidationMessage:
    return ValidationMessage(field=field, message=message)


def _suggestion(field: str, suggestion: str) -> ValidationSuggestion:
    return ValidationSuggestion(field=field, suggestion=suggestion)


def _subtopic_is_too_broad(subtopic: str, *, topic: str) -> bool:
    normalized_subtopic = _normalize_text(subtopic)
    normalized_topic = _normalize_text(topic)
    if normalized_subtopic == normalized_topic:
        return True
    if len(normalized_subtopic.split()) < 2:
        return True
    return normalized_subtopic in _BROADER_SUBTOPIC_TERMS


def _has_struggling_reader_context(learner_context: str) -> bool:
    normalized = _normalize_text(learner_context)
    return any(marker in normalized for marker in _STRUGGLING_READER_HINTS)


def validate_brief(brief: TeacherBrief, template: ResourceTemplate) -> BriefValidationResult:
    blockers: list[ValidationMessage] = []
    warnings: list[ValidationMessage] = []
    suggestions: list[ValidationSuggestion] = []

    if brief.intended_outcome not in template.allowed_outcomes:
        blockers.append(
            _message(
                field="intended_outcome",
                message=(
                    f"{template.label} is not meant for the "
                    f"'{brief.intended_outcome}' outcome."
                ),
            )
        )
        suggestions.append(
            _suggestion(
                "resource_type",
                "Choose a resource type that supports this outcome, or change the intended outcome.",
            )
        )

    broad_subtopics = [
        subtopic for subtopic in brief.subtopics if _subtopic_is_too_broad(subtopic, topic=brief.topic)
    ]
    if broad_subtopics:
        blockers.append(
            _message(
                field="subtopics",
                message="Pick narrower subtopics before generation. At least one selected focus is still too broad.",
            )
        )
        suggestions.append(
            _suggestion(
                "subtopics",
                "Make each subtopic specific enough to teach in one resource, such as one skill, comparison, or question.",
            )
        )

    if brief.resource_type == "exit_ticket" and brief.depth == "deep":
        warnings.append(
            _message(
                field="depth",
                message="Deep exit tickets tend to sprawl. Consider Standard depth or switch to a quiz.",
            )
        )
        suggestions.append(
            _suggestion(
                "resource_type",
                "If you need richer assessment coverage, switch from Exit Ticket to Quiz.",
            )
        )

    if brief.resource_type == "quick_explainer" and brief.depth == "deep":
        warnings.append(
            _message(
                field="depth",
                message="Deep coverage may outgrow a quick explainer. A mini booklet may fit better.",
            )
        )

    if brief.depth == "quick" and len(brief.supports) > 3:
        warnings.append(
            _message(
                field="supports",
                message="Quick resources usually work better with fewer supports. Too many may crowd the page.",
            )
        )

    if brief.resource_type == "exit_ticket" and "worked_examples" in brief.supports:
        warnings.append(
            _message(
                field="supports",
                message="Worked examples usually do not fit well inside an exit ticket.",
            )
        )
        suggestions.append(
            _suggestion(
                "supports",
                "Remove worked examples, or change the resource type to Worksheet if you want teaching plus checking.",
            )
        )

    if brief.resource_type == "quiz" and (
        "worked_examples" in brief.supports or "step_by_step" in brief.supports
    ):
        warnings.append(
            _message(
                field="supports",
                message="Scaffold-heavy supports can make a quiz feel like guided teaching instead of assessment.",
            )
        )
        suggestions.append(
            _suggestion(
                "resource_type",
                "Use Worksheet or Practice Set if you want the resource to teach and support before checking mastery.",
            )
        )

    if brief.resource_type == "practice_set" and brief.intended_outcome == "assess":
        warnings.append(
            _message(
                field="resource_type",
                message="Practice Set can check skill, but Quiz is a better fit for formal assessment.",
            )
        )

    if brief.resource_type == "mini_booklet" and _has_struggling_reader_context(
        brief.learner_context
    ):
        if "simpler_reading" not in brief.supports:
            warnings.append(
                _message(
                    field="supports",
                    message="This learner context suggests simpler reading support for a mini booklet.",
                )
            )
            suggestions.append(
                _suggestion(
                    "supports",
                    "Add Simpler reading support or consider a shorter Worksheet if learners need lighter reading.",
                )
            )

    if brief.resource_type in {"quiz", "exit_ticket"} and "discussion_questions" in brief.supports:
        warnings.append(
            _message(
                field="supports",
                message="Discussion questions are better suited to teaching or review resources than short assessments.",
            )
        )

    if brief.teacher_notes and len(brief.teacher_notes.split()) > 60:
        warnings.append(
            _message(
                field="teacher_notes",
                message="Teacher notes are getting long. Keep them focused on the few constraints the generator must honor.",
            )
        )

    return BriefValidationResult(
        is_ready=len(blockers) == 0,
        blockers=blockers,
        warnings=warnings,
        suggestions=suggestions,
    )
