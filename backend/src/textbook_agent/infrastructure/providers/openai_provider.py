import logging
from typing import Any

import openai

from textbook_agent.domain.ports.llm_provider import BaseProvider
from textbook_agent.domain.exceptions import ProviderConformanceError
from .json_utils import extract_json, to_strict_json_schema

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI LLM provider implementation with strict JSON Schema output."""

    def __init__(self, api_key: str = "", model: str = "gpt-5-mini") -> None:
        self.api_key = api_key
        self.model = model
        self._client = openai.OpenAI(api_key=api_key) if api_key else None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Any:
        if self._client is None:
            self._client = openai.OpenAI(api_key=self.api_key)

        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema.__name__.lower(),
                "strict": True,
                "schema": to_strict_json_schema(response_schema.model_json_schema()),
            },
        }

        request_kwargs = {
            "model": self.model,
            "max_completion_tokens": max_tokens,
            "response_format": response_format,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if not self.model.startswith("gpt-5"):
            request_kwargs["temperature"] = temperature

        response = self._client.chat.completions.create(**request_kwargs)

        raw_text = response.choices[0].message.content or ""
        logger.debug("OpenAI raw response: %s", raw_text[:500])

        try:
            data = extract_json(raw_text)
            return response_schema.model_validate(data)
        except Exception as exc:
            raise ProviderConformanceError(
                provider_name=self.model,
                schema_name=response_schema.__name__,
            ) from exc

    def name(self) -> str:
        return self.model
