from __future__ import annotations

import pytest
from pydantic import ValidationError

from learning.models import PackBriefRequest


def _valid_payload(**overrides) -> dict:
    payload = {
        "subject": "Science",
        "topic": "The Process of Germination",
        "subtopics": ["Seed Structure", "Conditions for Germination"],
        "grade_level": "grade_6",
        "grade_band": "middle_school",
        "class_profile": {
            "reading_level": "mixed",
            "language_support": "none",
            "confidence": "mixed",
            "prior_knowledge": "some_background",
            "pacing": "normal",
            "learning_preferences": [],
        },
        "learner_context": "Grade 6 learners with mixed reading levels.",
        "intended_outcome": "understand",
        "supports": ["visuals", "vocabulary_support"],
        "depth": "standard",
    }
    payload.update(overrides)
    return payload


def test_pack_brief_request_valid_without_resource_type() -> None:
    brief = PackBriefRequest(**_valid_payload())
    assert brief.intended_outcome == "understand"
    assert brief.depth == "standard"
    assert "visuals" in brief.supports


def test_pack_brief_request_rejects_unknown_outcome() -> None:
    with pytest.raises(ValidationError):
        PackBriefRequest(**_valid_payload(intended_outcome="invalid_outcome"))


def test_pack_brief_request_rejects_empty_subtopics() -> None:
    with pytest.raises(ValidationError):
        PackBriefRequest(**_valid_payload(subtopics=[]))


def test_pack_brief_request_rejects_empty_learner_context() -> None:
    with pytest.raises(ValidationError):
        PackBriefRequest(**_valid_payload(learner_context=""))


def test_pack_brief_request_accepts_all_valid_outcomes() -> None:
    for outcome in ("understand", "practice", "review", "assess", "compare", "vocabulary"):
        brief = PackBriefRequest(**_valid_payload(intended_outcome=outcome))
        assert brief.intended_outcome == outcome


def test_pack_brief_request_accepts_all_valid_depths() -> None:
    for depth in ("quick", "standard", "deep"):
        brief = PackBriefRequest(**_valid_payload(depth=depth))
        assert brief.depth == depth


def test_pack_brief_request_teacher_notes_optional() -> None:
    brief = PackBriefRequest(**_valid_payload())
    assert brief.teacher_notes is None

    brief_with_notes = PackBriefRequest(**_valid_payload(teacher_notes="Keep it short."))
    assert brief_with_notes.teacher_notes == "Keep it short."
