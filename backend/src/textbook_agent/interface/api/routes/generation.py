from fastapi import APIRouter, HTTPException

from textbook_agent.application.dtos import GenerationRequest, GenerationStatus

router = APIRouter(prefix="/api/v1", tags=["generation"])


@router.post("/generate")
async def generate_textbook(request: GenerationRequest):
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/status/{generation_id}")
async def get_generation_status(generation_id: str) -> GenerationStatus:
    raise HTTPException(status_code=501, detail="Not yet implemented")
