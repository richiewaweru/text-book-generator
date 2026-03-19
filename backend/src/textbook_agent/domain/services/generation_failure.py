from dataclasses import dataclass

from textbook_agent.domain.exceptions import (
    PipelineError,
    ProviderConformanceError,
    ProviderRequestError,
)


@dataclass(frozen=True)
class GenerationFailureClassification:
    error_type: str
    error_code: str | None = None


def classify_generation_failure(
    error: Exception | str,
) -> GenerationFailureClassification:
    if isinstance(error, ProviderRequestError):
        return GenerationFailureClassification(
            error_type="provider_error",
            error_code="provider_request_failed",
        )
    if isinstance(error, ProviderConformanceError):
        return GenerationFailureClassification(
            error_type="provider_error",
            error_code="provider_conformance_failed",
        )
    if isinstance(error, PipelineError):
        return GenerationFailureClassification(
            error_type="pipeline_error",
            error_code="pipeline_failed",
        )
    return classify_generation_error_message(str(error))


def classify_generation_error_message(_message: str) -> GenerationFailureClassification:
    return GenerationFailureClassification(
        error_type="unknown_error",
        error_code=None,
    )
