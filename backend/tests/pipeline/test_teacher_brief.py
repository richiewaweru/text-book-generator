from __future__ import annotations

import pytest

from pipeline.resources import get_resource_template, validate_brief
from pipeline.types.teacher_brief import TeacherBrief


def build_brief(**overrides) -> TeacherBrief:
    payload = {
        "subject": "Math",
        "topic": "Algebra",
        "subtopic": "Solving two-step equations",
        "learner_context": "Grade 7 students, mixed levels",
        "intended_outcome": "practice",
        "resource_type": "worksheet",
        "supports": ["worked_examples"],
        "depth": "standard",
        "teacher_notes": " Keep the examples short. ",
    }
    payload.update(overrides)
    return TeacherBrief.model_validate(payload)


@pytest.mark.parametrize(
    ("resource_type", "outcome"),
    [
        ("worksheet", "practice"),
        ("mini_booklet", "understand"),
        ("quick_explainer", "understand"),
        ("practice_set", "practice"),
        ("exit_ticket", "assess"),
        ("quiz", "assess"),
    ],
)
def test_resource_templates_accept_valid_briefs(resource_type: str, outcome: str) -> None:
    brief = build_brief(
        resource_type=resource_type,
        intended_outcome=outcome,
        supports=[] if resource_type in {"exit_ticket", "quiz"} else ["visuals"],
    )

    result = validate_brief(brief, get_resource_template(brief.resource_type))

    assert result.is_ready is True
    assert result.blockers == []


def test_quick_explainer_rejects_practice_outcome() -> None:
    brief = build_brief(resource_type="quick_explainer", intended_outcome="practice")

    result = validate_brief(brief, get_resource_template(brief.resource_type))

    assert result.is_ready is False
    assert any(message.field == "intended_outcome" for message in result.blockers)


def test_validator_blocks_broad_subtopic() -> None:
    brief = build_brief(subtopic="Algebra")

    result = validate_brief(brief, get_resource_template(brief.resource_type))

    assert result.is_ready is False
    assert any(message.field == "subtopic" for message in result.blockers)


def test_validator_warns_about_worked_examples_in_exit_tickets() -> None:
    brief = build_brief(
        resource_type="exit_ticket",
        intended_outcome="assess",
        supports=["worked_examples"],
    )

    result = validate_brief(brief, get_resource_template(brief.resource_type))

    assert result.is_ready is True
    assert any(message.field == "supports" for message in result.warnings)


def test_teacher_brief_trims_and_dedupes_values() -> None:
    brief = build_brief(
        subject=" Math ",
        topic=" Algebra ",
        subtopic=" Solving two-step equations ",
        learner_context=" Grade 7 mixed ability ",
        supports=["worked_examples", "worked_examples", "visuals"],
    )

    assert brief.subject == "Math"
    assert brief.topic == "Algebra"
    assert brief.subtopic == "Solving two-step equations"
    assert brief.learner_context == "Grade 7 mixed ability"
    assert brief.teacher_notes == "Keep the examples short."
    assert brief.supports == ["worked_examples", "visuals"]
