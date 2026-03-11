from typing import Any

from textbook_agent.domain.ports.llm_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    """Claude LLM provider implementation."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-6") -> None:
        self.api_key = api_key
        self.model = model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Any:
        raise NotImplementedError

    def name(self) -> str:
        return self.model
