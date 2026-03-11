from fastapi import APIRouter

from textbook_agent import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "version": __version__}
