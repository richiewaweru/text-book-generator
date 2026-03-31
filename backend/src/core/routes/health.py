from importlib.metadata import PackageNotFoundError, version
import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_async_session

try:
    __version__ = version("textbook-agent")
except PackageNotFoundError:
    __version__ = "0.1.0"

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


@router.get("/health/ready")
async def readiness_check(
    session: AsyncSession = Depends(get_async_session),
):
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover - exercised by tests with overrides
        checks["database"] = f"failed: {exc}"

    checks["anthropic_api_key"] = (
        "present" if os.getenv("ANTHROPIC_API_KEY") else "missing"
    )

    overall = (
        "ok"
        if all(value in {"ok", "present"} for value in checks.values())
        else "degraded"
    )
    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "checks": checks,
            "version": __version__,
        },
    )
