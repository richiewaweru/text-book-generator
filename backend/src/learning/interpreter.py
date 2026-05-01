from __future__ import annotations

from pydantic_ai import Agent

from learning.models import LearningJob, SituationRequest
from learning.prompts import (
    SITUATION_INTERPRETER_SYSTEM,
    build_situation_interpreter_user_prompt,
)
from pipeline.types.teacher_brief import GRADE_BAND_BY_LEVEL


async def interpret_situation(
    request: SituationRequest,
    *,
    model,
    run_llm_fn,
    generation_id: str = "",
) -> LearningJob:
    agent = Agent(
        model=model,
        output_type=LearningJob,
        system_prompt=SITUATION_INTERPRETER_SYSTEM,
    )
    result = await run_llm_fn(
        trace_id=generation_id,
        caller="learning_job_interpreter",
        agent=agent,
        model=model,
        user_prompt=build_situation_interpreter_user_prompt(request.situation),
    )
    output = result.output
    if output is None:
        raise ValueError("Interpreter returned no output.")
    output.grade_band = GRADE_BAND_BY_LEVEL.get(output.grade_level, "mixed")
    return output

