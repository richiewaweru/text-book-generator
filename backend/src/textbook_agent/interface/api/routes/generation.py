import uuid
import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from textbook_agent.application.dtos import (
    GenerationRequest,
    GenerationStatus,
    GenerationProgress,
)
from textbook_agent.interface.api.dependencies import get_use_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["generation"])

TOTAL_NODE_TYPES = 7


async def _run_generation(request: Request, generation_id: str, req: GenerationRequest):
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
        result = await use_case.execute(req, on_progress=on_progress)
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
async def generate_textbook(req: GenerationRequest, request: Request):
    generation_id = str(uuid.uuid4())
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    jobs[generation_id] = GenerationStatus(id=generation_id, status="pending")

    asyncio.create_task(_run_generation(request, generation_id, req))

    return {"generation_id": generation_id, "status": "pending"}


@router.get("/status/{generation_id}")
async def get_generation_status(generation_id: str, request: Request) -> GenerationStatus:
    jobs: dict[str, GenerationStatus] = request.app.state.jobs
    if generation_id not in jobs:
        raise HTTPException(status_code=404, detail="Generation not found")
    return jobs[generation_id]


@router.get("/textbook/{output_path:path}", response_class=HTMLResponse)
async def get_textbook_html(output_path: str):
    file_path = Path(output_path)
    if not file_path.exists() or not file_path.suffix == ".html":
        raise HTTPException(status_code=404, detail="Textbook not found")
    return HTMLResponse(content=file_path.read_text(encoding="utf-8"))
