import json
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.models import StudentProfileModel
from core.entities.student_profile import DeliveryPreferences, TeacherProfile
from core.ports.student_profile_repository import StudentProfileRepository
from core.value_objects import GradeBand, TeacherRole


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
        return TeacherProfile(
            id=model.id,
            user_id=model.user_id,
            teacher_role=TeacherRole(model.teacher_role),
            subjects=json.loads(model.subjects) if model.subjects else [],
            default_grade_band=GradeBand(model.default_grade_band),
            default_audience_description=model.default_audience_description or "",
            curriculum_framework=model.curriculum_framework or "",
            classroom_context=model.classroom_context or "",
            planning_goals=model.planning_goals or "",
            school_or_org_name=model.school_or_org_name or "",
            delivery_preferences=DeliveryPreferences.model_validate(
                json.loads(model.delivery_preferences) if model.delivery_preferences else {}
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
