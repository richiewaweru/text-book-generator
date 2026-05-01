from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import HTTPException

from core.config import settings
from core.database.models import LearningPackModel
from generation.service import (
    _context_from_planning_spec,
    _pipeline_sections_from_planning_spec,
    enqueue_generation,
)
from learning.models import LearningPackPlan, PackGenerateResponse, PackLearningPlan, ResourcePlan
from learning.pack_repository import LearningPackRepository
from pipeline.types.teacher_brief import ClassProfile, GRADE_BAND_BY_LEVEL, TeacherBrief
from planning.service import PlanningService

logger = logging.getLogger(__name__)


def _pack_context_prefix(
    *,
    plan: PackLearningPlan,
    job_type: str,
    resource_label: str,
    resource_order: int,
    total_resources: int,
    preceding_labels: list[str],
    following_labels: list[str],
    resource_purpose: str,
) -> str:
    lines = [
        f"Pack type: {job_type}",
        f"This resource: {resource_label} (resource {resource_order} of {total_resources})",
        f"Role in pack: {resource_purpose}",
    ]
    if preceding_labels:
        lines.append(f"Resources before this: {', '.join(preceding_labels)}")
        lines.append("Do not re-explain content already covered by preceding resources.")
    if following_labels:
        lines.append(f"Resources after this: {', '.join(following_labels)}")
    lines.extend(["", "Shared learning plan - all resources in this pack use this:"])
    lines.append(f"Objective: {plan.objective}")
    if plan.success_criteria:
        lines.append(f"Success criteria: {'; '.join(plan.success_criteria)}")
    if plan.prerequisite_skills:
        lines.append(f"Prerequisite skills: {'; '.join(plan.prerequisite_skills)}")
    if plan.likely_misconceptions:
        lines.append(f"Watch for: {'; '.join(plan.likely_misconceptions)}")
    if plan.shared_vocabulary:
        lines.append(f"Shared vocabulary: {', '.join(plan.shared_vocabulary)}")
    if plan.shared_examples:
        lines.append(f"Anchor examples: {'; '.join(plan.shared_examples)}")
    lines.append("")
    return "\n".join(lines)


def _brief_from_resource_plan(
    pack: LearningPackPlan,
    resource: ResourcePlan,
    learner_context: str,
) -> TeacherBrief:
    job = pack.learning_job
    profile = ClassProfile.model_validate(job.inferred_class_profile or {})
    return TeacherBrief(
        subject=job.subject,
        topic=job.topic,
        subtopics=[job.topic],
        grade_level=job.grade_level,
        grade_band=GRADE_BAND_BY_LEVEL.get(job.grade_level, "mixed"),
        class_profile=profile,
        learner_context=learner_context,
        intended_outcome=resource.intended_outcome,
        resource_type=resource.resource_type,
        supports=list(resource.supports),
        depth=resource.depth,
        teacher_notes=None,
    )


async def start_pack(
    pack: LearningPackPlan,
    learner_context: str,
    *,
    current_user,
    profile,
    engine,
    gen_repo,
    document_repo,
    report_repo,
    model,
    run_llm_fn,
    pack_repo: LearningPackRepository,
) -> PackGenerateResponse:
    active_count = await pack_repo.count_active_by_user(current_user.id)
    if active_count >= settings.learning_pack_max_active_per_user:
        raise ValueError("A pack is already generating. Wait for it to complete before starting another.")

    enabled = [resource for resource in pack.resources if resource.enabled]
    if not enabled:
        raise ValueError("No resources enabled in the pack.")

    pack_model = LearningPackModel(
        id=pack.pack_id,
        user_id=current_user.id,
        learning_job_type=pack.learning_job.job,
        subject=pack.learning_job.subject,
        topic=pack.learning_job.topic,
        pack_plan_json=pack.model_dump_json(),
        status="running",
        resource_count=len(enabled),
        completed_count=0,
        current_phase="queued",
        current_resource_label=enabled[0].label,
    )
    await pack_repo.create(pack_model)

    asyncio.create_task(
        run_pack(
            pack,
            learner_context,
            current_user=current_user,
            profile=profile,
            engine=engine,
            gen_repo=gen_repo,
            document_repo=document_repo,
            report_repo=report_repo,
            model=model,
            run_llm_fn=run_llm_fn,
            pack_repo=pack_repo,
        )
    )
    return PackGenerateResponse(pack_id=pack.pack_id, status="running")


async def run_pack(
    pack: LearningPackPlan,
    learner_context: str,
    *,
    current_user,
    profile,
    engine,
    gen_repo,
    document_repo,
    report_repo,
    model,
    run_llm_fn,
    pack_repo: LearningPackRepository,
) -> None:
    enabled = [resource for resource in pack.resources if resource.enabled]
    service = PlanningService()

    try:
        while True:
            generations = await pack_repo.generations_for_pack(pack.pack_id)
            by_resource_id = {
                generation.pack_resource_id: generation
                for generation in generations
                if generation.pack_resource_id
            }
            successful = [
                generation
                for generation in generations
                if generation.status in {"completed", "partial"}
            ]
            failed = [generation for generation in generations if generation.status == "failed"]
            active = [
                generation
                for generation in generations
                if generation.status in {"pending", "running"}
            ]

            if len(successful) + len(failed) >= len(enabled):
                final_status = "complete" if successful else "failed"
                await pack_repo.update_status(
                    pack.pack_id,
                    status=final_status,
                    completed_count=len(successful),
                    current_phase=None,
                    current_resource_label=None,
                )
                return

            user_active = await gen_repo.count_active_by_user(current_user.id)
            available_user_slots = max(settings.generation_max_concurrent_per_user - user_active, 0)
            available_pack_slots = max(
                settings.learning_pack_max_active_resources_per_pack - len(active),
                0,
            )
            slots = min(available_user_slots, available_pack_slots)
            pending = [resource for resource in enabled if resource.id not in by_resource_id]

            for resource in pending[:slots]:
                await _enqueue_resource(
                    pack,
                    resource,
                    enabled,
                    learner_context,
                    current_user=current_user,
                    profile=profile,
                    engine=engine,
                    gen_repo=gen_repo,
                    document_repo=document_repo,
                    report_repo=report_repo,
                    model=model,
                    run_llm_fn=run_llm_fn,
                    pack_repo=pack_repo,
                    service=service,
                )

            await pack_repo.update_status(
                pack.pack_id,
                completed_count=len(successful),
                current_phase="generating" if active else "queued",
                current_resource_label=(active[0].pack_resource_label if active else (pending[0].label if pending else None)),
            )
            await asyncio.sleep(settings.learning_pack_runner_poll_seconds)
    except Exception as exc:
        logger.exception("Learning pack runner failed pack_id=%s", pack.pack_id)
        await pack_repo.update_status(
            pack.pack_id,
            status="failed",
            current_phase=None,
            current_resource_label=None,
            error=str(exc),
        )


async def _enqueue_resource(
    pack: LearningPackPlan,
    resource: ResourcePlan,
    enabled: list[ResourcePlan],
    learner_context: str,
    *,
    current_user,
    profile,
    engine,
    gen_repo,
    document_repo,
    report_repo,
    model,
    run_llm_fn,
    pack_repo: LearningPackRepository,
    service: PlanningService,
) -> None:
    await pack_repo.update_status(
        pack.pack_id,
        current_phase="planning",
        current_resource_label=resource.label,
    )
    trace_id = uuid4().hex
    brief = _brief_from_resource_plan(pack, resource, learner_context)
    try:
        spec = await service.plan(
            brief,
            model=model,
            run_llm_fn=run_llm_fn,
            generation_id=trace_id,
        )
    except Exception:
        logger.exception("Planning failed for pack resource; using fallback")
        spec = service.fallback(brief, generation_id=trace_id)

    index = enabled.index(resource)
    pack_prefix = _pack_context_prefix(
        plan=pack.pack_learning_plan,
        job_type=pack.learning_job.job,
        resource_label=resource.label,
        resource_order=index + 1,
        total_resources=len(enabled),
        preceding_labels=[item.label for item in enabled[:index]],
        following_labels=[item.label for item in enabled[index + 1 :]],
        resource_purpose=resource.purpose,
    )
    context_str = pack_prefix + _context_from_planning_spec(spec)
    try:
        await enqueue_generation(
            current_user=current_user,
            profile=profile,
            engine=engine,
            gen_repo=gen_repo,
            document_repo=document_repo,
            report_repo=report_repo,
            subject=brief.subject,
            context=context_str,
            mode=spec.mode,
            template_id=spec.template_id,
            preset_id=spec.preset_id,
            section_count=len(spec.sections),
            section_plans=_pipeline_sections_from_planning_spec(spec),
            planning_spec_json=spec.model_dump_json(),
            sections_with_visuals=sum(1 for section in spec.sections if section.visual_placements),
            subtopics_covered=list(brief.subtopics),
            planning_warning=spec.warning,
            grade_band=brief.grade_band,
            learner_fit="general",
            pack_id=pack.pack_id,
            pack_resource_id=resource.id,
            pack_resource_label=resource.label,
            pack_objective=pack.pack_learning_plan.objective,
        )
    except HTTPException as exc:
        if exc.status_code == 429:
            logger.info("Pack resource enqueue deferred because generation slots are full")
            return
        raise
