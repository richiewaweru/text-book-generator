from __future__ import annotations

import pytest
from fastapi import HTTPException

from generation.v3_studio.supplement_rules import (
    allowed_supplements_for,
    assert_supplement_allowed,
    is_supplement_allowed,
    parent_resource_type_from_artifact,
)


def test_lesson_allows_exit_ticket_quiz_worksheet() -> None:
    specs = {"exit_ticket", "quiz", "worksheet", "lesson"}
    assert allowed_supplements_for("lesson", specs) == ["exit_ticket", "quiz", "worksheet"]


def test_exit_ticket_allows_none() -> None:
    specs = {"exit_ticket", "quiz", "worksheet"}
    assert allowed_supplements_for("exit_ticket", specs) == []


def test_missing_spec_filters_option_out() -> None:
    specs = {"exit_ticket", "lesson"}
    assert allowed_supplements_for("lesson", specs) == ["exit_ticket"]


def test_unknown_parent_defaults_to_lesson_matrix() -> None:
    specs = {"exit_ticket", "quiz", "worksheet", "lesson"}
    assert allowed_supplements_for("unknown_type", specs) == ["exit_ticket", "quiz", "worksheet"]


def test_assert_supplement_allowed_rejects_invalid_target() -> None:
    specs = {"exit_ticket", "quiz", "worksheet", "lesson"}
    with pytest.raises(HTTPException) as exc:
        assert_supplement_allowed(
            parent_resource_type="lesson",
            target_resource_type="revision_sheet",
            available_spec_ids=specs,
        )
    assert exc.value.status_code == 422


def test_assert_supplement_allowed_rejects_disallowed_matrix() -> None:
    specs = {"exit_ticket", "quiz", "worksheet"}
    with pytest.raises(HTTPException) as exc:
        assert_supplement_allowed(
            parent_resource_type="quiz",
            target_resource_type="exit_ticket",
            available_spec_ids=specs,
        )
    assert exc.value.status_code == 422


def test_parent_resource_type_from_artifact_prefers_derived() -> None:
    artifact = {
        "derived": {"resource_type": "mini_booklet"},
        "blueprint": {"lesson": {"resource_type": "lesson"}},
    }
    assert parent_resource_type_from_artifact(artifact) == "mini_booklet"


def test_is_supplement_allowed_requires_spec_and_matrix() -> None:
    specs = {"exit_ticket", "worksheet"}
    assert is_supplement_allowed(
        parent_resource_type="worksheet",
        target_resource_type="exit_ticket",
        available_spec_ids=specs,
    )
    assert not is_supplement_allowed(
        parent_resource_type="worksheet",
        target_resource_type="quiz",
        available_spec_ids=specs,
    )
