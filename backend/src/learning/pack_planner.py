from __future__ import annotations

from uuid import uuid4

from pydantic_ai import Agent

from core.config import settings
from learning.models import LearningJob, LearningPackPlan, PackLearningPlan, ResourcePlan
from learning.pack_spec_loader import get_pack_spec
from learning.pack_spec_schema import PackSpec
from learning.prompts import PACK_LEARNING_PLAN_SYSTEM, build_pack_learning_plan_user_prompt


async def generate_pack_learning_plan(
    job: LearningJob,
    *,
    model,
    run_llm_fn,
    generation_id: str = "",
) -> PackLearningPlan:
    spec = get_pack_spec(job.job)
    agent = Agent(
        model=model,
        output_type=PackLearningPlan,
        system_prompt=PACK_LEARNING_PLAN_SYSTEM,
    )
    result = await run_llm_fn(
        trace_id=generation_id,
        caller="pack_learning_planner",
        agent=agent,
        model=model,
        user_prompt=build_pack_learning_plan_user_prompt(
            job_type=job.job,
            subject=job.subject,
            topic=job.topic,
            grade_level=job.grade_level,
            objective_hint=job.objective,
            class_signals=job.class_signals,
            warnings=job.warnings,
            pack_intent=spec.intent,
        ),
    )
    output = result.output
    if output is None:
        raise ValueError("Pack learning plan returned no output.")
    return output


def plan_pack(
    job: LearningJob,
    pack_learning_plan: PackLearningPlan,
    *,
    max_resources: int | None = None,
) -> LearningPackPlan:
    spec = get_pack_spec(job.job)
    limit = max_resources or settings.learning_pack_max_resources
    resources = [
        ResourcePlan(
            id=uuid4().hex[:8],
            order=entry.order,
            resource_type=entry.resource_type,
            intended_outcome=entry.intended_outcome,
            label=entry.label,
            purpose=entry.purpose,
            depth=_resolve_depth(entry.depth, job),
            supports=list(job.inferred_supports) or list(spec.default_supports),
            enabled=True,
        )
        for entry in sorted(spec.resources, key=lambda item: item.order)[:limit]
    ]
    return LearningPackPlan(
        pack_id=uuid4().hex,
        learning_job=job,
        pack_learning_plan=pack_learning_plan,
        resources=resources,
        pack_rationale=_build_rationale(job, spec),
    )


def _resolve_depth(spec_depth: str, job: LearningJob) -> str:
    if spec_depth == "quick":
        return "quick"
    if spec_depth == "deep":
        return "deep"
    return job.recommended_depth


def _build_rationale(job: LearningJob, spec: PackSpec) -> str:
    first_line = spec.intent.strip().splitlines()[0] if spec.intent.strip() else spec.label
    return f"A {spec.label.lower()} for {job.topic} at {job.grade_level.replace('_', ' ')}. {first_line}"

