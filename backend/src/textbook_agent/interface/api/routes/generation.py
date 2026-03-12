import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from textbook_agent.application.dtos import (
    GenerationProgress,
    GenerationRequest,
    GenerationResultSummary,
    GenerationStatus,
)
from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.exceptions import PipelineError, ProviderConformanceError
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.interface.api.dependencies import (
    get_generation_repository,
    get_student_profile_repository,
    get_textbook_repository,
    get_use_case,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["generation"])

TOTAL_NODE_TYPES = 7


async def _run_generation(
    request: Request,
    generation_id: str,
    req: GenerationRequest,
    student_profile: StudentProfile | None,
    gen_repo: GenerationRepository,
):
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    completed_nodes: list[str] = []

    await gen_repo.update_status(generation_id, status="running")

    def on_progress(node_name: str):
        completed_nodes.append(node_name)
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="running",
            progress=GenerationProgress(
                current_node=node_name,
                completed_nodes=list(completed_nodes),
                total_nodes=TOTAL_NODE_TYPES,
            ),
        )

    try:
        use_case = get_use_case()
        result = await use_case.execute(
            req, student_profile=student_profile, on_progress=on_progress
        )
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="completed",
            result=GenerationResultSummary.from_response(result),
        )
        await gen_repo.update_status(
            generation_id,
            status="completed",
            output_path=result.output_path,
            quality_passed=(
                result.quality_report.passed if result.quality_report else None
            ),
            generation_time_seconds=result.generation_time_seconds,
        )
    except Exception as exc:
        logger.exception("Generation %s failed", generation_id)
        error_type = "unknown_error"
        if isinstance(exc, ProviderConformanceError):
            error_type = "provider_error"
        elif isinstance(exc, PipelineError):
            error_type = "pipeline_error"
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="failed",
            error=str(exc),
            error_type=error_type,
        )
        await gen_repo.update_status(
            generation_id,
            status="failed",
            error=str(exc),
        )


@router.post("/generate", status_code=202)
async def generate_textbook(
    req: GenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
):
    generation_id = str(uuid.uuid4())
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    jobs[generation_id] = GenerationStatus(id=generation_id, status="pending")

    student_profile = await profile_repo.find_by_user_id(current_user.id)

    await gen_repo.create(
        Generation(
            id=generation_id,
            user_id=current_user.id,
            subject=req.subject,
            context=req.context,
        )
    )

    asyncio.create_task(
        _run_generation(request, generation_id, req, student_profile, gen_repo)
    )

    return {"generation_id": generation_id, "status": "pending"}


@router.get("/status/{generation_id}")
async def get_generation_status(
    generation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> GenerationStatus:
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    if generation_id not in jobs:
        raise HTTPException(status_code=404, detail="Generation not found")
    return jobs[generation_id]


@router.get("/generations")
async def list_generations(
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    limit: int = 20,
    offset: int = 0,
):
    generations = await gen_repo.list_by_user(
        current_user.id, limit=limit, offset=offset
    )
    return [
        {
            "id": g.id,
            "subject": g.subject,
            "status": g.status,
            "quality_passed": g.quality_passed,
            "generation_time_seconds": g.generation_time_seconds,
            "created_at": g.created_at.isoformat() if g.created_at else None,
            "completed_at": g.completed_at.isoformat() if g.completed_at else None,
        }
        for g in generations
    ]


@router.get("/generations/{generation_id}")
async def get_generation_detail(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
):
    gen = await gen_repo.find_by_id(generation_id)
    if gen is None or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    return {
        "id": gen.id,
        "subject": gen.subject,
        "context": gen.context,
        "status": gen.status,
        "error": gen.error,
        "quality_passed": gen.quality_passed,
        "generation_time_seconds": gen.generation_time_seconds,
        "created_at": gen.created_at.isoformat() if gen.created_at else None,
        "completed_at": gen.completed_at.isoformat() if gen.completed_at else None,
    }


@router.get("/generations/{generation_id}/textbook", response_class=HTMLResponse)
async def get_textbook_html(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    textbook_repo: TextbookRepository = Depends(get_textbook_repository),
):
    generation = await gen_repo.find_by_id(generation_id)
    if generation is None or generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if generation.status != "completed" or not generation.output_path:
        raise HTTPException(status_code=409, detail="Textbook not ready")
    try:
        html = await textbook_repo.load_html(generation.output_path)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Textbook not found") from None
    return HTMLResponse(content=html)
