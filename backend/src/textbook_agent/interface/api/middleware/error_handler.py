import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from textbook_agent.domain.exceptions import (
    NodeValidationError,
    PipelineError,
    ProviderConformanceError,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProviderConformanceError)
    async def handle_provider_error(
        request: Request, exc: ProviderConformanceError
    ) -> JSONResponse:
        logger.error("Provider conformance error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": str(exc),
                "error_type": "provider_error",
                "detail": f"The LLM provider '{exc.provider_name}' could not produce a valid response for '{exc.schema_name}'.",
            },
        )

    @app.exception_handler(NodeValidationError)
    async def handle_validation_error(
        request: Request, exc: NodeValidationError
    ) -> JSONResponse:
        logger.error("Node validation error: %s", exc)
        return JSONResponse(
            status_code=422,
            content={
                "error": str(exc),
                "error_type": "validation_error",
                "detail": f"Pipeline node '{exc.node_name}' failed validation: {exc.reason}",
            },
        )

    @app.exception_handler(PipelineError)
    async def handle_pipeline_error(
        request: Request, exc: PipelineError
    ) -> JSONResponse:
        logger.error("Pipeline error: %s", exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": str(exc),
                "error_type": "pipeline_error",
                "detail": f"Pipeline node '{exc.node_name}' failed: {exc.reason}",
            },
        )
