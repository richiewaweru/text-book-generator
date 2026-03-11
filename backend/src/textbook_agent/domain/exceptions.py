class PipelineError(Exception):
    """Raised when a pipeline node fails after retries."""

    def __init__(self, node_name: str, reason: str) -> None:
        self.node_name = node_name
        self.reason = reason
        super().__init__(f"Pipeline node '{node_name}' failed: {reason}")


class NodeValidationError(PipelineError):
    """Raised when a node's input or output fails Pydantic validation."""

    pass


class ProviderConformanceError(Exception):
    """Raised when an LLM provider cannot return data conforming to the expected schema."""

    def __init__(self, provider_name: str, schema_name: str) -> None:
        self.provider_name = provider_name
        self.schema_name = schema_name
        super().__init__(
            f"Provider '{provider_name}' could not conform to schema '{schema_name}'"
        )
