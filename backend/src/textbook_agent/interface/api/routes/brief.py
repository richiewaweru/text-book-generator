from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from pipeline.contracts import get_contract, list_template_ids, validate_preset_for_template
from pipeline.llm_runner import run_llm
from pipeline.providers.registry import get_node_text_model
from pipeline.types.requests import GenerationMode as PipelineGenerationMode
from textbook_agent.application.dtos import BriefRequest, GenerationSpec
from textbook_agent.application.services.brief_planner_service import (
    BriefPlannerService,
    TemplateSummary,
)
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.interface.api.dependencies import get_student_profile_repository
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/v1", tags=["brief"])


def _live_safe_templates() -> list[TemplateSummary]:
    templates: list[TemplateSummary] = []
    for template_id in list_template_ids():
        if not validate_preset_for_template(template_id, "blue-classroom"):
            continue
        contract = get_contract(template_id)
        templates.append(
            TemplateSummary(
                id=contract.id,
                name=contract.name,
                intent=contract.intent,
                learner_fit=list(contract.learner_fit),
            )
        )
    return templates


async def _load_profile(
    user: User,
    profile_repo: StudentProfileRepository,
) -> StudentProfile | None:
    return await profile_repo.find_by_user_id(user.id)


@router.post("/brief", response_model=GenerationSpec)
async def create_brief(
    brief: BriefRequest,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
) -> GenerationSpec:
    profile = await _load_profile(current_user, profile_repo)
    templates = _live_safe_templates()
    if not templates:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No live-safe templates are available for blue-classroom.",
        )

    model = get_node_text_model(
        "brief_planner",
        generation_mode=PipelineGenerationMode.DRAFT,
    )

    service = BriefPlannerService()
    return await service.plan(
        brief,
        profile=profile,
        templates=templates,
        model=model,
        run_llm_fn=run_llm,
    )
