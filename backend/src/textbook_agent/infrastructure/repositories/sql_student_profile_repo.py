import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)
from textbook_agent.infrastructure.database.models import StudentProfileModel


class SqlStudentProfileRepository(StudentProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_user_id(self, user_id: str) -> StudentProfile | None:
        stmt = select(StudentProfileModel).where(StudentProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def create(self, profile: StudentProfile) -> StudentProfile:
        now = datetime.now(timezone.utc)
        model = StudentProfileModel(
            id=profile.id or str(uuid.uuid4()),
            user_id=profile.user_id,
            age=profile.age,
            education_level=profile.education_level.value,
            interests=json.dumps(profile.interests),
            learning_style=profile.learning_style.value,
            preferred_notation=profile.preferred_notation.value,
            prior_knowledge=profile.prior_knowledge,
            goals=profile.goals,
            preferred_depth=profile.preferred_depth.value,
            learner_description=profile.learner_description,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, profile: StudentProfile) -> StudentProfile:
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.user_id == profile.user_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        model.age = profile.age
        model.education_level = profile.education_level.value
        model.interests = json.dumps(profile.interests)
        model.learning_style = profile.learning_style.value
        model.preferred_notation = profile.preferred_notation.value
        model.prior_knowledge = profile.prior_knowledge
        model.goals = profile.goals
        model.preferred_depth = profile.preferred_depth.value
        model.learner_description = profile.learner_description
        model.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: StudentProfileModel) -> StudentProfile:
        return StudentProfile(
            id=model.id,
            user_id=model.user_id,
            age=model.age,
            education_level=EducationLevel(model.education_level),
            interests=json.loads(model.interests) if model.interests else [],
            learning_style=LearningStyle(model.learning_style),
            preferred_notation=NotationLanguage(model.preferred_notation),
            prior_knowledge=model.prior_knowledge or "",
            goals=model.goals or "",
            preferred_depth=Depth(model.preferred_depth),
            learner_description=model.learner_description or "",
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
