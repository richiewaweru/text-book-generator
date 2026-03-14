from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Abstract LLM provider interface. All LLM calls go through this port.

    The domain defines this interface; infrastructure provides concrete adapters
    (AnthropicProvider, OpenAIProvider). Swapping providers is a config change.
    """

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> Any:
        """Make a completion call. Always returns a validated Pydantic instance."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return provider identifier string e.g. 'claude-sonnet-4-6'."""
        ...
