import asyncio
import logging
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from textbook_agent.application.dtos import (
    EnhanceGenerationRequest,
    GenerationProgress,
    GenerationRequest,
    GenerationResultSummary,
    GenerationStatus,
)
from textbook_agent.domain.entities.generation import Generation
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.textbook import RawTextbook
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.exceptions import (
    PipelineError,
    ProviderConformanceError,
    ProviderRequestError,
)
from textbook_agent.domain.ports.generation_repository import GenerationRepository
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.domain.ports.textbook_repository import TextbookRepository
from textbook_agent.domain.value_objects import GenerationMode
from textbook_agent.interface.api.dependencies import (
    get_generation_repository,
    get_settings,
    get_student_profile_repository,
    get_textbook_repository,
    get_use_case,
)
from textbook_agent.interface.api.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["generation"])


def _history_item(generation: Generation) -> dict:
    return {
        "id": generation.id,
        "subject": generation.subject,
        "status": generation.status,
        "mode": generation.mode,
        "source_generation_id": generation.source_generation_id,
        "quality_passed": generation.quality_passed,
        "generation_time_seconds": generation.generation_time_seconds,
        "created_at": generation.created_at.isoformat() if generation.created_at else None,
        "completed_at": generation.completed_at.isoformat() if generation.completed_at else None,
    }


def _detail_item(generation: Generation) -> dict:
    return {
        "id": generation.id,
        "subject": generation.subject,
        "context": generation.context,
        "status": generation.status,
        "mode": generation.mode,
        "source_generation_id": generation.source_generation_id,
        "error": generation.error,
        "quality_passed": generation.quality_passed,
        "generation_time_seconds": generation.generation_time_seconds,
        "created_at": generation.created_at.isoformat() if generation.created_at else None,
        "completed_at": generation.completed_at.isoformat() if generation.completed_at else None,
    }


async def _run_generation(
    request: Request,
    generation_id: str,
    req: GenerationRequest,
    student_profile: StudentProfile | None,
    gen_repo: GenerationRepository,
    *,
    mode: GenerationMode,
    source_generation_id: str | None = None,
):
    jobs: dict[str, GenerationStatus] = request.app.state.jobs

    await gen_repo.update_status(generation_id, status="running")

    def on_progress(progress: GenerationProgress):
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="running",
            mode=progress.mode,
            progress=progress,
            source_generation_id=source_generation_id,
        )

    try:
        use_case = get_use_case()
        result = await use_case.execute(
            req, student_profile=student_profile, on_progress=on_progress
        )
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="completed",
            mode=result.mode,
            result=GenerationResultSummary.from_response(result),
            source_generation_id=source_generation_id,
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
        if isinstance(exc, (ProviderConformanceError, ProviderRequestError)):
            error_type = "provider_error"
        elif isinstance(exc, PipelineError):
            error_type = "pipeline_error"
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="failed",
            mode=mode,
            error=str(exc),
            error_type=error_type,
            source_generation_id=source_generation_id,
        )
        await gen_repo.update_status(
            generation_id,
            status="failed",
            error=str(exc),
        )


async def _run_enhancement(
    request: Request,
    generation_id: str,
    req: EnhanceGenerationRequest,
    source_textbook: RawTextbook,
    gen_repo: GenerationRepository,
    *,
    source_generation_id: str,
):
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    await gen_repo.update_status(generation_id, status="running")

    def on_progress(progress: GenerationProgress):
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="running",
            mode=progress.mode,
            progress=progress,
            source_generation_id=source_generation_id,
        )

    try:
        use_case = get_use_case()
        result = await use_case.enhance(
            req,
            source_textbook,
            on_progress=on_progress,
            source_generation_id=source_generation_id,
        )
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="completed",
            mode=result.mode,
            result=GenerationResultSummary.from_response(result),
            source_generation_id=source_generation_id,
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
        logger.exception("Enhancement %s failed", generation_id)
        error_type = "unknown_error"
        if isinstance(exc, (ProviderConformanceError, ProviderRequestError)):
            error_type = "provider_error"
        elif isinstance(exc, PipelineError):
            error_type = "pipeline_error"
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="failed",
            mode=req.target_mode,
            error=str(exc),
            error_type=error_type,
            source_generation_id=source_generation_id,
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
    mode = req.resolved_mode()
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    jobs[generation_id] = GenerationStatus(
        id=generation_id,
        status="pending",
        mode=mode,
    )

    student_profile = await profile_repo.find_by_user_id(current_user.id)

    await gen_repo.create(
        Generation(
            id=generation_id,
            user_id=current_user.id,
            subject=req.subject,
            context=req.context,
            mode=mode,
        )
    )

    asyncio.create_task(
        _run_generation(
            request,
            generation_id,
            req,
            student_profile,
            gen_repo,
            mode=mode,
        )
    )

    return {"generation_id": generation_id, "status": "pending", "mode": mode}


@router.post("/generations/{generation_id}/enhance", status_code=202)
async def enhance_generation(
    generation_id: str,
    request: Request,
    req: EnhanceGenerationRequest = Body(...),
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
    textbook_repo: TextbookRepository = Depends(get_textbook_repository),
):
    source_generation = await gen_repo.find_by_id(generation_id)
    if source_generation is None or source_generation.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    if source_generation.mode != GenerationMode.DRAFT:
        raise HTTPException(status_code=409, detail="Only draft generations can be enhanced")
    if source_generation.status != "completed" or not source_generation.output_path:
        raise HTTPException(status_code=409, detail="Draft is not ready for enhancement")

    try:
        source_textbook = await textbook_repo.load_textbook(source_generation.output_path)
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Draft artifact not found") from None

    child_generation_id = str(uuid.uuid4())
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    jobs[child_generation_id] = GenerationStatus(
        id=child_generation_id,
        status="pending",
        mode=req.target_mode,
        source_generation_id=generation_id,
    )

    await gen_repo.create(
        Generation(
            id=child_generation_id,
            user_id=current_user.id,
            subject=source_generation.subject,
            context=source_generation.context,
            mode=req.target_mode,
            source_generation_id=generation_id,
        )
    )

    asyncio.create_task(
        _run_enhancement(
            request,
            child_generation_id,
            req,
            source_textbook,
            gen_repo,
            source_generation_id=generation_id,
        )
    )

    return {
        "generation_id": child_generation_id,
        "status": "pending",
        "mode": req.target_mode,
        "source_generation_id": generation_id,
    }


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
    limit: int = get_settings().default_pagination_limit,
    offset: int = 0,
):
    generations = await gen_repo.list_by_user(
        current_user.id, limit=limit, offset=offset
    )
    return [_history_item(generation) for generation in generations]


@router.get("/generations/{generation_id}")
async def get_generation_detail(
    generation_id: str,
    current_user: User = Depends(get_current_user),
    gen_repo: GenerationRepository = Depends(get_generation_repository),
):
    gen = await gen_repo.find_by_id(generation_id)
    if gen is None or gen.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Generation not found")
    return _detail_item(gen)


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
