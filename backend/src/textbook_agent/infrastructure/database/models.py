import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    picture_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    profile = relationship("StudentProfileModel", back_populates="user", uselist=False)
    generations = relationship("GenerationModel", back_populates="user")


class StudentProfileModel(Base):
    __tablename__ = "student_profiles"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    age = Column(Integer, nullable=False)
    education_level = Column(String, nullable=False)
    interests = Column(Text, default="[]")
    learning_style = Column(String, nullable=False)
    preferred_notation = Column(String, default="plain")
    prior_knowledge = Column(Text, default="")
    goals = Column(Text, default="")
    preferred_depth = Column(String, default="standard")
    learner_description = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("UserModel", back_populates="profile")

    def get_interests_list(self) -> list[str]:
        return json.loads(self.interests) if self.interests else []

    def set_interests_list(self, values: list[str]) -> None:
        self.interests = json.dumps(values)


class GenerationModel(Base):
    __tablename__ = "generations"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    context = Column(Text, default="")
    mode = Column(String, default="balanced", nullable=False)
    status = Column(String, default="pending")
    document_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    error_type = Column(String, nullable=True, index=True)
    error_code = Column(String, nullable=True, index=True)
    requested_template_id = Column(String, nullable=False, index=True)
    resolved_template_id = Column(String, nullable=True, index=True)
    requested_preset_id = Column(String, nullable=False, index=True)
    resolved_preset_id = Column(String, nullable=True, index=True)
    section_count = Column(Integer, nullable=True)
    quality_passed = Column(Boolean, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)
    source_generation_id = Column(String, nullable=True, index=True)
    planning_spec_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("UserModel", back_populates="generations")
