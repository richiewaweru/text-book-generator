import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from textbook_agent.application.dtos import (
    GenerationProgress,
    GenerationRequest,
    GenerationStatus,
)
from textbook_agent.domain.entities.student_profile import StudentProfile
from textbook_agent.domain.entities.user import User
from textbook_agent.domain.ports.student_profile_repository import StudentProfileRepository
from textbook_agent.interface.api.dependencies import (
    get_student_profile_repository,
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
):
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    completed_nodes: list[str] = []

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
            result=result,
        )
    except Exception as exc:
        logger.exception("Generation %s failed", generation_id)
        jobs[generation_id] = GenerationStatus(
            id=generation_id,
            status="failed",
            error=str(exc),
        )


@router.post("/generate", status_code=202)
async def generate_textbook(
    req: GenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    profile_repo: StudentProfileRepository = Depends(get_student_profile_repository),
):
    generation_id = str(uuid.uuid4())
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    jobs[generation_id] = GenerationStatus(id=generation_id, status="pending")

    student_profile = await profile_repo.find_by_user_id(current_user.id)

    asyncio.create_task(
        _run_generation(request, generation_id, req, student_profile)
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


@router.get("/textbook/{output_path:path}", response_class=HTMLResponse)
async def get_textbook_html(
    output_path: str,
    current_user: User = Depends(get_current_user),
):
    file_path = Path(output_path)
    if not file_path.exists() or not file_path.suffix == ".html":
        raise HTTPException(status_code=404, detail="Textbook not found")
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))
