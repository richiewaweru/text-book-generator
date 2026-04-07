from __future__ import annotations

import asyncio
import logging
from time import perf_counter

from core.health.routes import DependencyStatus
from pipeline.providers.gemini_image_client import (
    get_gemini_image_client,
    resolve_gemini_image_api_key,
)
from pipeline.storage.image_store import get_image_store

logger = logging.getLogger(__name__)

_IMAGE_PROBE_PROMPT = (
    "Create a simple classroom-safe diagnostic image: a single black dot centered on a white "
    "background, no text, no extra objects."
)
_IMAGE_PROBE_TIMEOUT_SECONDS = 45.0


async def check_gemini_image_provider() -> DependencyStatus:
    start = perf_counter()
    api_key = resolve_gemini_image_api_key()
    if not api_key:
        return DependencyStatus(
            name="gemini_image",
            status="degraded",
            detail=(
                "Missing GOOGLE_CLOUD_NANO_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY."
            ),
        )

    try:
        client = get_gemini_image_client()
    except Exception as exc:  # pragma: no cover - exercised via tests
        logger.warning("Gemini image readiness check failed", exc_info=exc)
        return DependencyStatus(
            name="gemini_image",
            status="degraded",
            detail=f"{type(exc).__name__}: {exc}",
        )

    return DependencyStatus(
        name="gemini_image",
        status="ok",
        latency_ms=round((perf_counter() - start) * 1000, 1),
        detail=f"model={client.MODEL}",
    )


async def check_image_store() -> DependencyStatus:
    start = perf_counter()
    try:
        store = get_image_store()
    except Exception as exc:  # pragma: no cover - exercised via tests
        logger.warning("Image store readiness check failed during init", exc_info=exc)
        return DependencyStatus(
            name="image_store",
            status="degraded",
            detail=f"{type(exc).__name__}: {exc}",
        )

    ok, detail = await store.probe_write_access()
    return DependencyStatus(
        name="image_store",
        status="ok" if ok else "degraded",
        latency_ms=round((perf_counter() - start) * 1000, 1),
        detail=detail or store.describe_target(),
    )


async def run_image_probe() -> tuple[list[DependencyStatus], int | None]:
    start = perf_counter()
    probe_image_bytes: int | None = None
    api_key = resolve_gemini_image_api_key()
    if not api_key:
        gemini_status = DependencyStatus(
            name="gemini_image_probe",
            status="degraded",
            detail=(
                "Missing GOOGLE_CLOUD_NANO_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY."
            ),
        )
    else:
        try:
            client = get_gemini_image_client()
            result = await asyncio.wait_for(
                client.generate_image(
                    prompt=_IMAGE_PROBE_PROMPT,
                    size="1024x1024",
                    format="png",
                ),
                timeout=_IMAGE_PROBE_TIMEOUT_SECONDS,
            )
            gemini_status = DependencyStatus(
                name="gemini_image_probe",
                status="ok",
                latency_ms=round((perf_counter() - start) * 1000, 1),
                detail=f"model={client.MODEL}",
            )
            probe_image_bytes = len(result.bytes)
        except Exception as exc:  # pragma: no cover - exercised via tests
            logger.warning("Gemini image probe failed", exc_info=exc)
            gemini_status = DependencyStatus(
                name="gemini_image_probe",
                status="unreachable",
                detail=f"{type(exc).__name__}: {exc}",
            )
            probe_image_bytes = None

    store_start = perf_counter()
    try:
        store = get_image_store()
    except Exception as exc:  # pragma: no cover - exercised via tests
        logger.warning("Image store probe failed during init", exc_info=exc)
        image_store_status = DependencyStatus(
            name="image_store_probe",
            status="unreachable",
            detail=f"{type(exc).__name__}: {exc}",
        )
    else:
        ok, detail = await store.probe_write_access()
        image_store_status = DependencyStatus(
            name="image_store_probe",
            status="ok" if ok else "unreachable",
            latency_ms=round((perf_counter() - store_start) * 1000, 1),
            detail=detail or store.describe_target(),
        )

    return [gemini_status, image_store_status], probe_image_bytes
