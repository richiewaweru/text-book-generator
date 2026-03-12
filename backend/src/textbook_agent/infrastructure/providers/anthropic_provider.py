import logging
from typing import Any

import anthropic

from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.exceptions import ProviderConformanceError
from .json_utils import extract_json, to_strict_json_schema

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Claude LLM provider implementation."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Any:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=self.api_key)

        tool_name = f"return_{response_schema.__name__.lower()}"
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Return a response that matches the {response_schema.__name__} schema.",
                    "input_schema": to_strict_json_schema(
                        response_schema.model_json_schema()
                    ),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )

        try:
            data = None
            for block in message.content:
                if getattr(block, "type", None) == "tool_use":
                    data = block.input
                    break

            if data is None:
                raw_text = message.content[0].text
                logger.debug("Anthropic raw response: %s", raw_text[:500])
                data = extract_json(raw_text)

            return response_schema.model_validate(data)
        except Exception as exc:
            raise ProviderConformanceError(
                provider_name=self.model,
                schema_name=response_schema.__name__,
            ) from exc

    def name(self) -> str:
        return self.model
