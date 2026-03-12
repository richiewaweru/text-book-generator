from typing import Literal

from pydantic import BaseModel


class PracticeProblem(BaseModel):
    """A short learner exercise paired with a non-solution hint."""

    difficulty: Literal["warm", "medium", "cold"]
    statement: str
    hint: str
