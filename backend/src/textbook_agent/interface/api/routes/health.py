from fastapi import APIRouter, Request

from textbook_agent import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request):
    started_at = getattr(request.app.state, "started_at", None)
    return {
        "status": "ok",
        "version": __version__,
        "instance_id": getattr(request.app.state, "instance_id", None),
        "started_at": started_at.isoformat() if started_at else None,
        "pipeline_architecture": getattr(
            request.app.state,
            "pipeline_architecture",
            None,
        ),
    }
