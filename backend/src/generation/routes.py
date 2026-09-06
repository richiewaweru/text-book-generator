from __future__ import annotations

from fastapi import APIRouter

from generation.block_generate_routes import block_generate_router
from generation.canonical_routes import router as canonical_router
from generation.retirement import router as legacy_v3_router

router = APIRouter(prefix="/api/v1", tags=["generation"])
router.include_router(legacy_v3_router)
router.include_router(canonical_router)
router.include_router(block_generate_router)
