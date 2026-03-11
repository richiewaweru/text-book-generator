from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)


class TestStudentProfile:
    def test_valid_profile(self):
        now = datetime.now(timezone.utc)
        profile = StudentProfile(
            id="sp-1",
            user_id="u-1",
            age=16,
            education_level=EducationLevel.HIGH_SCHOOL,
            interests=["gaming", "music"],
            learning_style=LearningStyle.VISUAL,
            preferred_notation=NotationLanguage.PLAIN,
            prior_knowledge="Basic algebra",
            goals="Pass SAT math",
            preferred_depth=Depth.STANDARD,
            created_at=now,
            updated_at=now,
        )
        assert profile.age == 16
        assert profile.education_level == EducationLevel.HIGH_SCHOOL
        assert len(profile.interests) == 2

    def test_rejects_invalid_age(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            StudentProfile(
                id="sp-1",
                user_id="u-1",
                age=5,
                education_level=EducationLevel.ELEMENTARY,
                learning_style=LearningStyle.VISUAL,
                created_at=now,
                updated_at=now,
            )

    def test_defaults(self):
        now = datetime.now(timezone.utc)
        profile = StudentProfile(
            id="sp-1",
            user_id="u-1",
            age=20,
            education_level=EducationLevel.UNDERGRADUATE,
            learning_style=LearningStyle.READING_WRITING,
            created_at=now,
            updated_at=now,
        )
        assert profile.interests == []
        assert profile.prior_knowledge == ""
        assert profile.goals == ""
        assert profile.preferred_depth == Depth.STANDARD
        assert profile.preferred_notation == NotationLanguage.PLAIN


class TestUser:
    def test_valid_user(self):
        now = datetime.now(timezone.utc)
        user = User(
            id="u-1",
            email="test@example.com",
            name="Test",
            created_at=now,
            updated_at=now,
        )
        assert user.email == "test@example.com"
        assert user.has_profile is False

    def test_user_with_profile(self):
        now = datetime.now(timezone.utc)
        user = User(
            id="u-1",
            email="test@example.com",
            has_profile=True,
            created_at=now,
            updated_at=now,
        )
        assert user.has_profile is True


class TestEducationLevel:
    def test_all_values(self):
        expected = {
            "elementary", "middle_school", "high_school",
            "undergraduate", "graduate", "professional",
        }
        assert {e.value for e in EducationLevel} == expected


class TestLearningStyle:
    def test_all_values(self):
        expected = {"visual", "reading_writing", "kinesthetic", "auditory"}
        assert {s.value for s in LearningStyle} == expected
