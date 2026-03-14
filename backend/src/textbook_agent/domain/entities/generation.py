from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from textbook_agent.domain.value_objects import GenerationMode


class Generation(BaseModel):
    """A textbook generation job record.

    Persistent entity stored in the database to track generation
    lifecycle from pending through completion or failure.
    """

    id: str
    user_id: str
    subject: str
    context: str = ""
    mode: GenerationMode = GenerationMode.BALANCED
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    output_path: str | None = None
    error: str | None = None
    quality_passed: bool | None = None
    generation_time_seconds: float | None = None
    source_generation_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
