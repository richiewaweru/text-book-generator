import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import StudentProfileModel
from core.entities.student_profile import DeliveryPreferences, TeacherProfile
from core.ports.student_profile_repository import StudentProfileRepository
from core.value_objects import GradeBand, TeacherRole

logger = logging.getLogger(__name__)


def _safe_json_loads(raw: str | None, fallback):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return fallback


def _safe_teacher_role(raw: str | None) -> TeacherRole:
    try:
        return TeacherRole(raw or TeacherRole.TEACHER.value)
    except ValueError:
        logger.warning("Unknown legacy teacher_role '%s'; defaulting to teacher", raw)
        return TeacherRole.TEACHER


def _safe_grade_band(raw: str | None) -> GradeBand:
    try:
        return GradeBand(raw or GradeBand.HIGH_SCHOOL.value)
    except ValueError:
        logger.warning("Unknown legacy default_grade_band '%s'; defaulting to high_school", raw)
        return GradeBand.HIGH_SCHOOL


class SqlStudentProfileRepository(StudentProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_user_id(self, user_id: str) -> TeacherProfile | None:
        stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def create(self, profile: TeacherProfile) -> TeacherProfile:
        now = datetime.utcnow()
        model = StudentProfileModel(
            id=profile.id or str(uuid.uuid4()),
            user_id=profile.user_id,
            teacher_role=profile.teacher_role.value,
            subjects=json.dumps(profile.subjects),
            default_grade_band=profile.default_grade_band.value,
            default_audience_description=profile.default_audience_description,
            curriculum_framework=profile.curriculum_framework,
            classroom_context=profile.classroom_context,
            planning_goals=profile.planning_goals,
            school_or_org_name=profile.school_or_org_name,
            delivery_preferences=profile.delivery_preferences.model_dump_json(),
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, profile: TeacherProfile) -> TeacherProfile:
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == profile.user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        model.teacher_role = profile.teacher_role.value
        model.subjects = json.dumps(profile.subjects)
        model.default_grade_band = profile.default_grade_band.value
        model.default_audience_description = profile.default_audience_description
        model.curriculum_framework = profile.curriculum_framework
        model.classroom_context = profile.classroom_context
        model.planning_goals = profile.planning_goals
        model.school_or_org_name = profile.school_or_org_name
        model.delivery_preferences = profile.delivery_preferences.model_dump_json()
        model.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: StudentProfileModel) -> TeacherProfile:
        subjects = _safe_json_loads(model.subjects, [])
        if not isinstance(subjects, list):
            subjects = []

        raw_preferences = _safe_json_loads(model.delivery_preferences, {})
        if not isinstance(raw_preferences, dict):
            raw_preferences = {}

        return TeacherProfile(
            id=model.id,
            user_id=model.user_id,
            teacher_role=_safe_teacher_role(model.teacher_role),
            subjects=[str(subject).strip() for subject in subjects if str(subject).strip()],
            default_grade_band=_safe_grade_band(model.default_grade_band),
            default_audience_description=model.default_audience_description or "",
            curriculum_framework=model.curriculum_framework or "",
            classroom_context=model.classroom_context or "",
            planning_goals=model.planning_goals or "",
            school_or_org_name=model.school_or_org_name or "",
            delivery_preferences=DeliveryPreferences.model_validate(
                raw_preferences
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
