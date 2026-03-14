import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.exceptions import (
    NodeValidationError,
    PipelineError,
    ProviderRequestError,
)

logger = logging.getLogger(__name__)

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound=BaseModel)


class PipelineNode(ABC, Generic[TInput, TOutput]):
    """Abstract base for all pipeline nodes.

    Each node defines typed input/output schemas enforced by Pydantic.
    The execute() method handles validation and retry logic around the
    abstract run() method that subclasses implement.
    """

    input_schema: type[TInput]
    output_schema: type[TOutput]
    retry_on_failure: bool = True
    max_retries: int = 2
    retry_base_delay: float = 1.0

    def __init__(self, provider: BaseProvider | None = None) -> None:
        self.provider = provider

    @abstractmethod
    async def run(self, input_data: TInput) -> TOutput:
        """Execute the node's core logic. Subclasses must implement this."""
        ...

    async def execute(self, input_data: TInput) -> TOutput:
        """Validate input, run the node with retry logic, validate output."""
        try:
            validated_input = self.input_schema.model_validate(
                input_data if isinstance(input_data, dict) else input_data.model_dump()
            )
        except Exception as e:
            raise NodeValidationError(
                node_name=self.__class__.__name__,
                reason=f"Input validation failed: {e}",
            )

        last_error: Exception | None = None
        attempts = (self.max_retries + 1) if self.retry_on_failure else 1

        for attempt in range(attempts):
            try:
                result = await self.run(validated_input)
                self.output_schema.model_validate(
                    result if isinstance(result, dict) else result.model_dump()
                )
                return result
            except NodeValidationError:
                raise
            except ProviderRequestError:
                raise
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    delay = self.retry_base_delay * (2**attempt)
                    logger.warning(
                        "%s attempt %d failed, retrying in %.1fs: %s",
                        self.__class__.__name__,
                        attempt + 1,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)

        raise PipelineError(
            node_name=self.__class__.__name__,
            reason=f"Failed after {attempts} attempt(s): {last_error}",
        )
