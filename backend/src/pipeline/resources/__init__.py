from pipeline.resources.resource_validator import validate_brief
from pipeline.types.teacher_brief import (
    BriefValidationResult as ValidationResult,
    ValidationMessage,
    ValidationSuggestion,
)
from resource_specs.loader import get_spec

__all__ = [
    "ValidationMessage",
    "ValidationResult",
    "ValidationSuggestion",
    "get_spec",
    "validate_brief",
]
