from datetime import datetime, timezone
from types import SimpleNamespace

from core.repositories.sql_student_profile_repo import SqlStudentProfileRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestSqlStudentProfileRepository:
    def test_to_entity_normalizes_legacy_profile_rows(self):
        model = SimpleNamespace(
            id="profile-1",
            user_id="user-1",
            teacher_role=None,
            subjects='{"not":"a-list"}',
            default_grade_band=None,
            default_audience_description=None,
            curriculum_framework=None,
            classroom_context=None,
            planning_goals=None,
            school_or_org_name=None,
            delivery_preferences='{"tone":"supportive","use_visuals":true,"keep_short":true}',
            created_at=_now(),
            updated_at=_now(),
        )

        entity = SqlStudentProfileRepository._to_entity(model)

        assert entity.teacher_role.value == "teacher"
        assert entity.subjects == []
        assert entity.default_grade_band.value == "high_school"
        assert entity.default_audience_description == ""
        assert entity.delivery_preferences.tone == "supportive"
        assert entity.delivery_preferences.use_visuals is True
        assert entity.delivery_preferences.keep_short is True

    def test_to_entity_falls_back_for_invalid_json_and_unknown_enums(self):
        model = SimpleNamespace(
            id="profile-2",
            user_id="user-2",
            teacher_role="legacy-role",
            subjects='{"broken"',
            default_grade_band="legacy-band",
            default_audience_description="",
            curriculum_framework="",
            classroom_context="",
            planning_goals="",
            school_or_org_name="",
            delivery_preferences='{"broken"',
            created_at=_now(),
            updated_at=_now(),
        )

        entity = SqlStudentProfileRepository._to_entity(model)

        assert entity.teacher_role.value == "teacher"
        assert entity.subjects == []
        assert entity.default_grade_band.value == "high_school"
        assert entity.delivery_preferences.tone == "supportive"
