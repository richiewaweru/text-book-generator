from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from pipeline.contracts import get_contract, list_template_ids, validate_preset_for_template
from pipeline.llm_runner import run_llm
from pipeline.providers.registry import get_node_text_model
from pipeline.types.requests import GenerationMode as PipelineGenerationMode
from planning import PlanningService, PlanningTemplateContract, StudioBriefRequest
from planning.models import PlanningGenerationSpec
from textbook_agent.application.dtos import (
    BriefRequest,
    GenerationAcceptedResponse,
    GenerationSpec,
)
from textbook_agent.application.services.brief_planner_service import (
    BriefPlannerService,
    TemplateSummary,
)
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.ports.document_repository import DocumentRepository
from textbook_agent.domain.ports.generation_report_repository import (
    GenerationReportRepository,
)
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.value_objects import GenerationMode
from textbook_agent.interface.api.dependencies import (
    get_document_repository,
    get_generation_repository,
    get_report_repository,
    get_student_profile_repository,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user
from textbook_agent.interface.api.routes.generation import (
    _context_from_planning_spec,
    _pipeline_sections_from_planning_spec,
    enqueue_generation,
)

router = APIRouter(prefix="/api/v1", tags=["brief"])
logger = logging.getLogger(__name__)


def _legacy_live_safe_templates() -> list[TemplateSummary]:
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


def _planning_live_safe_templates() -> list[PlanningTemplateContract]:
    templates: list[PlanningTemplateContract] = []
    for template_id in list_template_ids():
        if not validate_preset_for_template(template_id, "blue-classroom"):
            continue
        contract = get_contract(template_id)
        templates.append(PlanningTemplateContract.model_validate(contract.model_dump(mode="json")))
    return templates


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _load_profile(
    user: User,
    profile_repo: StudentProfileRepository,
) -> StudentProfile | None:
    return await profile_repo.find_by_user_id(user.id)


@router.post("/brief", response_model=GenerationSpec)
async def create_brief(
    brief: BriefRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
) -> GenerationSpec:
    logger.warning(
        "Deprecated POST /api/v1/brief used by user_id=%s; prefer /api/v1/brief/stream + /api/v1/brief/commit",
        current_user.id,
    )
    response.headers["Deprecation"] = "true"
    response.headers["Warning"] = (
        '299 - "Deprecated endpoint; use /api/v1/brief/stream and /api/v1/brief/commit."'
    )

    profile = await _load_profile(current_user, profile_repo)
    templates = _legacy_live_safe_templates()
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


@router.post("/brief/stream")
async def stream_brief(
    brief: StudioBriefRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    templates = _planning_live_safe_templates()
    if not templates:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No live-safe templates are available for blue-classroom.",
        )

    model = get_node_text_model(
        "brief_planner",
        generation_mode=PipelineGenerationMode.DRAFT,
    )
    service = PlanningService()

    async def stream():
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        async def emit(payload: dict) -> None:
            await queue.put(payload)

        async def run() -> None:
            try:
                spec = await service.plan(
                    brief,
                    contracts=templates,
                    model=model,
                    run_llm_fn=run_llm,
                    emit=emit,
                    llm_generation_mode=PipelineGenerationMode.DRAFT,
                )
                await queue.put(
                    {
                        "event": "plan_complete",
                        "data": {"spec": spec.model_dump(mode="json")},
                    }
                )
            except Exception:
                fallback = service.fallback(brief, contracts=templates)
                await queue.put(
                    {
                        "event": "plan_error",
                        "data": {
                            "spec": fallback.model_dump(mode="json"),
                            "warning": fallback.warning,
                        },
                    }
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run())
        try:
            while True:
                payload = await queue.get()
                if payload is None:
                    break
                yield _sse_event(payload["event"], payload["data"])
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/contracts", response_model=list[PlanningTemplateContract])
async def list_contracts(
    current_user: User = Depends(get_current_user),
) -> list[PlanningTemplateContract]:
    _ = current_user
    return _planning_live_safe_templates()


@router.post("/brief/commit", response_model=GenerationAcceptedResponse)
async def commit_brief(
    spec: PlanningGenerationSpec,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    document_repo: DocumentRepository = Depends(get_document_repository),
    report_repo: GenerationReportRepository = Depends(get_report_repository),
) -> GenerationAcceptedResponse:
    profile = await _load_profile(current_user, profile_repo)
    committed = spec.model_copy(update={"status": "committed"})
    return await enqueue_generation(
        current_user=current_user,
        profile=profile,
        gen_repo=gen_repo,
        document_repo=document_repo,
        report_repo=report_repo,
        subject=committed.source_brief.intent,
        context=_context_from_planning_spec(
            committed,
            subject=committed.source_brief.intent,
        ),
        mode=GenerationMode.BALANCED,
        template_id=committed.template_id,
        preset_id=committed.preset_id,
        section_count=len(committed.sections),
        section_plans=_pipeline_sections_from_planning_spec(committed),
        planning_spec_json=committed.model_dump_json(),
    )
