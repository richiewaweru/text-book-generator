import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.value_objects import (
    Depth,
    EducationLevel,
    LearningStyle,
    NotationLanguage,
)
from textbook_agent.interface.api.dependencies import get_student_profile_repository
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


class ProfileCreateRequest(BaseModel):
    age: int = Field(ge=8, le=99)
    education_level: EducationLevel
    interests: list[str] = Field(default_factory=list)
    learning_style: LearningStyle
    preferred_notation: NotationLanguage = NotationLanguage.PLAIN
    prior_knowledge: str = ""
    goals: str = ""
    preferred_depth: Depth = Depth.STANDARD
    learner_description: str = ""


class ProfileUpdateRequest(BaseModel):
    age: int | None = Field(default=None, ge=8, le=99)
    education_level: EducationLevel | None = None
    interests: list[str] | None = None
    learning_style: LearningStyle | None = None
    preferred_notation: NotationLanguage | None = None
    prior_knowledge: str | None = None
    goals: str | None = None
    preferred_depth: Depth | None = None
    learner_description: str | None = None


@router.get("", response_model=StudentProfile)
async def get_profile(
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
):
    profile = await profile_repo.find_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Complete onboarding first.",
        )
    return profile


@router.post("", response_model=StudentProfile, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
):
    existing = await profile_repo.find_by_user_id(current_user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile already exists. Use PATCH to update.",
        )

    now = datetime.now(timezone.utc)
    profile = StudentProfile(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        age=body.age,
        education_level=body.education_level,
        interests=body.interests,
        learning_style=body.learning_style,
        preferred_notation=body.preferred_notation,
        prior_knowledge=body.prior_knowledge,
        goals=body.goals,
        preferred_depth=body.preferred_depth,
        learner_description=body.learner_description,
        created_at=now,
        updated_at=now,
    )
    return await profile_repo.create(profile)


@router.patch("", response_model=StudentProfile)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
):
    existing = await profile_repo.find_by_user_id(current_user.id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )

    update_data = body.model_dump(exclude_none=True)
    updated = existing.model_copy(update=update_data)
    updated.updated_at = datetime.now(timezone.utc)
    return await profile_repo.update(updated)
