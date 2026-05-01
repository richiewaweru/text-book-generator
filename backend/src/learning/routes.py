from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from core.auth.middleware import get_current_user
from core.database.models import LearningPackModel
from core.database.session import async_session_factory
from core.dependencies import get_student_profile_repository, get_settings
from core.entities.user import User
from core.llm import build_model, run_llm
from core.rate_limit import limiter
from generation.dependencies import (
    get_document_repository,
    get_generation_engine,
    get_generation_repository,
    get_report_repository,
)
from generation.ports.generation_repository import GenerationRepository
from learning.models import (
    LearningJob,
    LearningPackPlan,
    PackGenerateRequest,
    PackGenerateResponse,
    PackLearningPlan,
    PackStatusResponse,
    ResourceStatus,
)
from learning.pack_planner import generate_pack_learning_plan, plan_pack
from learning.pack_repository import LearningPackRepository
from learning.pack_runner import start_pack
from pipeline.types.teacher_brief import TeacherBrief
from planning.llm_config import PLANNING_SECTION_COMPOSER_CALLER, get_planning_slot, get_planning_spec
from planning.routes import _load_profile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/packs", tags=["learning-packs"])


def get_pack_repository() -> LearningPackRepository:
    return LearningPackRepository(async_session_factory)


async def _run_llm_fn(**kwargs):
    caller = kwargs.get("caller", PLANNING_SECTION_COMPOSER_CALLER)
    return await run_llm(
        slot=get_planning_slot(caller),
        spec=get_planning_spec(caller),
        **kwargs,
    )


_OUTCOME_TO_JOB: dict[str, str] = {
    "understand": "introduce",
    "practice": "practice",
    "review": "reteach",
    "assess": "assess",
    "compare": "introduce",
    "vocabulary": "introduce",
}


def _brief_to_learning_job(brief: TeacherBrief) -> LearningJob:
    profile = brief.class_profile
    signals: list[str] = []
    if profile.reading_level == "below_grade":
        signals.append("below grade reading level")
    if profile.language_support in ("some_ell", "many_ell"):
        signals.append(f"{profile.language_support.replace('_', ' ')} students")
    if profile.confidence == "low":
        signals.append("low confidence")
    if profile.prior_knowledge == "new_topic":
        signals.append("first exposure to this topic")
    if profile.pacing == "short_chunks":
        signals.append("needs shorter tasks")

    return LearningJob(
        job=_OUTCOME_TO_JOB.get(brief.intended_outcome, "introduce"),
        subject=brief.subject or brief.topic,
        topic=brief.topic,
        grade_level=brief.grade_level,
        grade_band=brief.grade_band,
        objective=brief.subtopics[0] if brief.subtopics else brief.topic,
        class_signals=signals,
        assumptions=[],
        warnings=[],
        recommended_depth=brief.depth,
        inferred_supports=list(brief.supports),
        inferred_class_profile=profile.model_dump(),
    )


@router.post("/plan-from-brief", response_model=LearningPackPlan)
@limiter.limit("20/minute")
async def plan_pack_from_brief(
    request: Request,
    brief: TeacherBrief,
    current_user: User = Depends(get_current_user),
) -> LearningPackPlan:
    _ = (request, current_user)
    trace_id = uuid.uuid4().hex
    model = build_model(get_planning_spec(PLANNING_SECTION_COMPOSER_CALLER))
    job = _brief_to_learning_job(brief)
    try:
        pack_learning_plan = await generate_pack_learning_plan(
            job,
            model=model,
            run_llm_fn=_run_llm_fn,
            generation_id=trace_id,
        )
    except Exception:
        logger.exception("Pack learning plan LLM failed; using minimal fallback")
        pack_learning_plan = PackLearningPlan(
            objective=job.objective,
            success_criteria=[],
            prerequisite_skills=[],
            likely_misconceptions=[],
            shared_vocabulary=[],
            shared_examples=[],
        )
    return plan_pack(job, pack_learning_plan)


@router.post("/generate", response_model=PackGenerateResponse)
@limiter.limit("10/minute")
async def generate_learning_pack(
    request: Request,
    payload: PackGenerateRequest,
    current_user: User = Depends(get_current_user),
    profile_repo=Depends(get_student_profile_repository),
    engine=Depends(get_generation_engine),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo=Depends(get_document_repository),
    report_repo=Depends(get_report_repository),
    pack_repo: LearningPackRepository = Depends(get_pack_repository),
) -> PackGenerateResponse:
    _ = request
    enabled = [resource for resource in payload.pack_plan.resources if resource.enabled]
    if not enabled:
        raise HTTPException(status_code=422, detail="No resources enabled.")
    if len(enabled) > get_settings().learning_pack_max_resources:
        raise HTTPException(status_code=422, detail="Too many resources enabled.")

    profile = await _load_profile(current_user, profile_repo)
    model = build_model(get_planning_spec(PLANNING_SECTION_COMPOSER_CALLER))
    try:
        return await start_pack(
            payload.pack_plan,
            payload.learner_context,
            current_user=current_user,
            profile=profile,
            engine=engine,
            gen_repo=gen_repo,
            document_repo=document_repo,
            report_repo=report_repo,
            model=model,
            run_llm_fn=_run_llm_fn,
            pack_repo=pack_repo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[PackStatusResponse])
async def list_packs(
    current_user: User = Depends(get_current_user),
    pack_repo: LearningPackRepository = Depends(get_pack_repository),
    limit: int = 20,
) -> list[PackStatusResponse]:
    packs = await pack_repo.list_by_user(current_user.id, limit=limit)
    return [_pack_to_status(pack, []) for pack in packs]


@router.get("/{pack_id}", response_model=PackStatusResponse)
async def get_pack_status(
    pack_id: str,
    current_user: User = Depends(get_current_user),
    pack_repo: LearningPackRepository = Depends(get_pack_repository),
) -> PackStatusResponse:
    pack = await pack_repo.find_by_id(pack_id)
    if pack is None or pack.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Pack not found.")
    generations = await pack_repo.generations_for_pack(pack_id)
    return _pack_to_status(pack, generations)


def _pack_to_status(pack: LearningPackModel, generations: list) -> PackStatusResponse:
    plan_data = json.loads(pack.pack_plan_json)
    resource_rows = [
        resource for resource in plan_data.get("resources", []) if resource.get("enabled", True)
    ]
    generations_by_resource = {
        generation.pack_resource_id: generation
        for generation in generations
        if generation.pack_resource_id
    }
    resources: list[ResourceStatus] = []
    for resource in resource_rows:
        gen = generations_by_resource.get(resource["id"])
        if gen is None:
            phase = "planning" if (
                pack.current_phase == "planning"
                and pack.current_resource_label == resource["label"]
            ) else "pending"
            resources.append(
                ResourceStatus(
                    resource_id=resource["id"],
                    generation_id=None,
                    label=resource["label"],
                    resource_type=resource["resource_type"],
                    status="pending",
                    phase=phase,
                )
            )
            continue
        phase = (
            "done"
            if gen.status in {"completed", "partial"}
            else "failed"
            if gen.status == "failed"
            else "generating"
        )
        resources.append(
            ResourceStatus(
                resource_id=resource["id"],
                generation_id=gen.id,
                label=gen.pack_resource_label or resource["label"],
                resource_type=resource["resource_type"],
                status=gen.status,
                phase=phase,
            )
        )
    return PackStatusResponse(
        pack_id=pack.id,
        status=pack.status,
        learning_job_type=pack.learning_job_type,
        subject=pack.subject,
        topic=pack.topic,
        resource_count=pack.resource_count,
        completed_count=pack.completed_count,
        current_phase=pack.current_phase,
        current_resource_label=pack.current_resource_label,
        resources=resources,
        created_at=pack.created_at.isoformat(),
        completed_at=pack.completed_at.isoformat() if pack.completed_at else None,
    )
